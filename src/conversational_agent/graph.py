from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from conversational_agent.config import get_settings
from conversational_agent.digest import get_digest_store
from conversational_agent.entities import extract_active_entities
from conversational_agent.executor import DeterministicRestExecutor
from conversational_agent.models import PendingCall, PlannerDecision
from conversational_agent.planner import choose_next_action
from conversational_agent.policy import approved, confirmation_required
from conversational_agent.state import AgentState
from conversational_agent.validation import OperationValidator


settings = get_settings()
digest = get_digest_store()
validator = OperationValidator(digest)
executor = DeterministicRestExecutor(digest, validator)


def _latest_human_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage) or getattr(message, "type", "") in {"human", "user"}:
            content = message.content
            return content if isinstance(content, str) else json.dumps(content, default=str)
    return ""


def _bounded(value: Any, limit: int) -> Any:
    rendered = json.dumps(value, ensure_ascii=False, default=str)
    if len(rendered) <= limit:
        return value
    return {
        "truncated": True,
        "original_character_count": len(rendered),
        "preview": rendered[:limit] + "…",
    }


def prepare_turn(state: AgentState) -> dict[str, Any]:
    """Runs once for each new user run; an interrupt resume continues after the interrupt instead."""
    return {
        "decision": None,
        "pending_call": None,
        "last_api_result": None,
        "step_count": 0,
        "validation_feedback": None,
        "turn_trace": [],
        "api_history": state.get("api_history", []),
        "active_entities": state.get("active_entities", {}),
    }


async def decide(state: AgentState) -> dict[str, Any]:
    step_count = state.get("step_count", 0)
    if step_count >= settings.max_agent_steps:
        decision = PlannerDecision(
            kind="respond",
            message=(
                "I reached the per-turn operation limit before I could complete this safely. "
                "No additional operation was executed. Please narrow the request or continue in a new message."
            ),
            confidence=1.0,
        )
        return {"decision": decision.model_dump()}

    latest = _latest_human_text(state.get("messages", []))
    # Include runtime error/result vocabulary in retrieval so follow-up planning sees related digest rules.
    retrieval_query = latest
    if state.get("last_api_result"):
        retrieval_query += " " + json.dumps(state["last_api_result"], default=str)[:4000]
    digest_context = digest.planner_context(retrieval_query)

    decision = await choose_next_action(
        messages=state.get("messages", []),
        digest_context=digest_context,
        active_entities=state.get("active_entities", {}),
        last_api_result=state.get("last_api_result"),
        api_history=state.get("api_history", []),
        validation_feedback=state.get("validation_feedback"),
        step_count=step_count,
        max_steps=settings.max_agent_steps,
    )

    trace = list(state.get("turn_trace", []))
    trace.append(
        {
            "node": "decide",
            "step": step_count + 1,
            "kind": decision.kind,
            "operation_id": decision.operation_id,
            "confidence": decision.confidence,
        }
    )
    return {
        "decision": decision.model_dump(),
        "step_count": step_count + 1,
        "validation_feedback": None,
        "turn_trace": trace,
    }


def route_decision(state: AgentState) -> Literal["emit_response", "validate_call"]:
    decision = PlannerDecision.model_validate(state.get("decision") or {})
    if decision.kind == "invoke":
        return "validate_call"
    return "emit_response"


def emit_response(state: AgentState) -> dict[str, Any]:
    decision = PlannerDecision.model_validate(state.get("decision") or {})
    if decision.kind == "clarify":
        text = decision.message or "I need one more detail before I can continue."
    else:
        text = decision.message or "Done."
    return {"messages": [AIMessage(content=text)], "pending_call": None}


def validate_call(state: AgentState) -> dict[str, Any]:
    decision = PlannerDecision.model_validate(state.get("decision") or {})
    if not decision.operation_id:
        return {
            "validation_feedback": "Planner selected invoke without an operation_id.",
            "pending_call": None,
        }

    call = PendingCall(
        operation_id=decision.operation_id,
        path_params=decision.path_params,
        query_params=decision.query_params,
        body=decision.body,
        inferred_fields=decision.inferred_fields,
    )
    issues = validator.validate_call(call)
    if issues:
        return {
            "validation_feedback": "The proposed service call was blocked by deterministic validation: " + "; ".join(issues),
            "pending_call": None,
        }

    trace = list(state.get("turn_trace", []))
    trace.append({"node": "validate_call", "operation_id": call.operation_id, "status": "accepted"})
    return {"pending_call": call.model_dump(), "validation_feedback": None, "turn_trace": trace}


def route_validation(state: AgentState) -> Literal["decide", "safety_gate"]:
    if state.get("pending_call") is None:
        return "decide"
    return "safety_gate"


def safety_gate(state: AgentState) -> dict[str, Any]:
    call = PendingCall.model_validate(state["pending_call"])
    decision = PlannerDecision.model_validate(state["decision"])
    operation = digest.get_operation(call.operation_id) or {}
    execution = operation.get("execution", {})

    if not confirmation_required(
        operation,
        inferred_fields=decision.inferred_fields,
        confidence=decision.confidence,
        confirm_conditional_actions=settings.confirm_conditional_actions,
    ):
        return {}

    confirmation_payload = {
        "type": "operation_confirmation",
        "operation_id": call.operation_id,
        "purpose": operation.get("purpose"),
        "effect": execution.get("effect"),
        "risk": execution.get("risk"),
        "method": operation.get("http", {}).get("method"),
        "path": operation.get("http", {}).get("path"),
        "resolved_arguments": {
            "path_params": call.path_params,
            "query_params": call.query_params,
            "body": call.body,
        },
        "inferred_fields": call.inferred_fields,
        "instruction": "Approve to execute this exact resolved operation, or reject it.",
    }
    answer = interrupt(confirmation_payload)
    if not approved(answer):
        trace = list(state.get("turn_trace", []))
        trace.append({"node": "safety_gate", "operation_id": call.operation_id, "status": "rejected"})
        return {
            "messages": [AIMessage(content=f"I did not execute `{call.operation_id}` because it was not approved.")],
            "pending_call": None,
            "decision": {"kind": "respond", "message": "Action rejected", "confidence": 1.0},
            "turn_trace": trace,
        }

    trace = list(state.get("turn_trace", []))
    trace.append({"node": "safety_gate", "operation_id": call.operation_id, "status": "approved"})
    return {"turn_trace": trace}


def route_safety(state: AgentState) -> Literal["execute_call", "end_after_rejection"]:
    if state.get("pending_call") is None:
        return "end_after_rejection"
    return "execute_call"


def end_after_rejection(state: AgentState) -> dict[str, Any]:
    return {}


async def execute_call(state: AgentState) -> dict[str, Any]:
    call = PendingCall.model_validate(state["pending_call"])
    result = await executor.execute(call)
    result_dict = result.model_dump()
    bounded = _bounded(result_dict, settings.max_api_result_chars)

    history = list(state.get("api_history", []))
    history.append(bounded)
    history = history[-20:]

    active = dict(state.get("active_entities", {}))
    if result.ok:
        active.update(extract_active_entities(result.data))

    trace = list(state.get("turn_trace", []))
    trace.append(
        {
            "node": "execute_call",
            "operation_id": call.operation_id,
            "ok": result.ok,
            "status_code": result.status_code,
        }
    )
    return {
        "last_api_result": bounded,
        "api_history": history,
        "active_entities": active,
        "pending_call": None,
        "validation_feedback": None,
        "turn_trace": trace,
    }


builder = StateGraph(AgentState)
builder.add_node("prepare_turn", prepare_turn)
builder.add_node("decide", decide)
builder.add_node("emit_response", emit_response)
builder.add_node("validate_call", validate_call)
builder.add_node("safety_gate", safety_gate)
builder.add_node("execute_call", execute_call)
builder.add_node("end_after_rejection", end_after_rejection)

builder.add_edge(START, "prepare_turn")
builder.add_edge("prepare_turn", "decide")
builder.add_conditional_edges(
    "decide",
    route_decision,
    {"emit_response": "emit_response", "validate_call": "validate_call"},
)
builder.add_edge("emit_response", END)
builder.add_conditional_edges(
    "validate_call",
    route_validation,
    {"decide": "decide", "safety_gate": "safety_gate"},
)
builder.add_conditional_edges(
    "safety_gate",
    route_safety,
    {"execute_call": "execute_call", "end_after_rejection": "end_after_rejection"},
)
builder.add_edge("end_after_rejection", END)
builder.add_edge("execute_call", "decide")

# Agent Server injects its own checkpointer/store. Do not supply a checkpointer here.
graph = builder.compile()
