from __future__ import annotations

from typing import Any, Annotated
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    # Studio recognizes a conventional messages field and renders it as chat.
    messages: Annotated[list[Any], add_messages]

    decision: dict[str, Any] | None
    pending_call: dict[str, Any] | None
    last_api_result: dict[str, Any] | None
    api_history: list[dict[str, Any]]
    active_entities: dict[str, str]

    step_count: int
    validation_feedback: str | None
    turn_trace: list[dict[str, Any]]
