from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import get_settings
from .models import PlannerDecision


SYSTEM_PROMPT = """You are the planning brain of a conversational interface to exactly one REST microservice.

Your ONLY service knowledge comes from the Service Digest context supplied in each request and runtime API results.
Never invent endpoints, operation IDs, entity IDs, schemas, business rules, or current runtime data.

Choose exactly one next step:
- respond: answer the user using digest knowledge and/or API results already obtained.
- invoke: select ONE canonical operation_id from the operation catalog and provide exact path/query/body arguments.
- clarify: ask a concise question when a required value cannot be safely resolved.

Rules:
1. Questions about stable service purpose, API capabilities, business rules, states, schemas, errors, or workflows should normally be answered from the digest without API calls.
2. Questions about CURRENT customers, products, stock, orders, shipments, returns, refunds, or timelines require read-only API operations.
3. For user requests that change state, use read operations first when necessary to resolve phrases such as 'my latest order', 'that shipment', or an ambiguous item.
4. Never invent an ID. Use list/get operations to resolve it, or ask the user. The service has no authenticated customer identity, so phrases like 'my order' require a known customer_id from conversation context; otherwise ask which customer rather than assuming a demo identity.
5. Use only the HTTP operation metadata from the digest. Never propose a raw URL or method.
6. Put path parameters, query parameters, and JSON body fields in their correct structures. Do not put a path ID in the body unless the digest explicitly requires it. When an operation has no path parameters use {}, when it has no query parameters use {}, and when there are no inferred fields use []. Never use null for those collection fields.
7. inferred_fields must list arguments obtained from prior conversation state/API results rather than explicitly stated in the user's latest message.
8. If an API call failed, inspect the error and digest semantics. Do not blindly repeat the same failing call.
9. Choose only one API operation at a time. After its result, you will be called again and can decide the next step.
10. Do not expose hidden reasoning. The message field is only user-facing text.
11. If a confirmation interrupt will be required, still choose invoke. The deterministic graph enforces confirmation.
12. Never claim an action succeeded before receiving a successful API result.
"""


@lru_cache(maxsize=1)
def get_structured_model():
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to run the conversational agent")
    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        timeout=60,
        max_retries=2,
    )
    return model.with_structured_output(PlannerDecision, method="function_calling")


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, default=str)


def format_recent_conversation(messages: list[BaseMessage], limit: int = 12) -> str:
    lines: list[str] = []
    for message in messages[-limit:]:
        role = getattr(message, "type", message.__class__.__name__)
        lines.append(f"{role.upper()}: {_message_text(message)}")
    return "\n".join(lines)


async def choose_next_action(
    *,
    messages: list[BaseMessage],
    digest_context: str,
    active_entities: dict[str, str],
    last_api_result: dict[str, Any] | None,
    api_history: list[dict[str, Any]],
    validation_feedback: str | None,
    step_count: int,
    max_steps: int,
) -> PlannerDecision:
    model = get_structured_model()
    conversation = format_recent_conversation(messages)
    runtime_context = {
        "active_entities": active_entities,
        "last_api_result": last_api_result,
        "recent_api_history": api_history[-5:],
        "validation_feedback": validation_feedback,
        "step": step_count,
        "max_steps": max_steps,
    }

    user_payload = f"""SERVICE DIGEST CONTEXT (authoritative):
{digest_context}

RECENT CONVERSATION:
{conversation}

RUNTIME CONTEXT:
{json.dumps(runtime_context, indent=2, ensure_ascii=False, default=str)}

Choose the single next step now.
"""
    result = await model.ainvoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_payload)])
    return result
