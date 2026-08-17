from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


Scalar = str | int | float | bool | None


class PlannerDecision(BaseModel):
    """Exactly one next step chosen by the LLM planner."""

    kind: Literal["respond", "invoke", "clarify"]
    message: str | None = Field(
        default=None,
        description="User-facing response/question for respond or clarify. Omit for invoke.",
    )
    operation_id: str | None = Field(
        default=None,
        description="Canonical operation ID from the service digest when kind=invoke.",
    )
    path_params: dict[str, Scalar] = Field(default_factory=dict)
    query_params: dict[str, Scalar] = Field(default_factory=dict)
    body: dict[str, Any] | list[Any] | None = None
    inferred_fields: list[str] = Field(
        default_factory=list,
        description="Argument fields resolved from context/runtime data rather than stated explicitly in the latest message.",
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)

    @field_validator("path_params", "query_params", mode="before")
    @classmethod
    def normalize_optional_dicts(cls, value):
        return {} if value is None else value

    @field_validator("inferred_fields", mode="before")
    @classmethod
    def normalize_optional_lists(cls, value):
        return [] if value is None else value


class PendingCall(BaseModel):
    operation_id: str
    path_params: dict[str, Scalar] = Field(default_factory=dict)
    query_params: dict[str, Scalar] = Field(default_factory=dict)
    body: dict[str, Any] | list[Any] | None = None
    inferred_fields: list[str] = Field(default_factory=list)

    @field_validator("path_params", "query_params", mode="before")
    @classmethod
    def normalize_optional_dicts(cls, value):
        return {} if value is None else value

    @field_validator("inferred_fields", mode="before")
    @classmethod
    def normalize_optional_lists(cls, value):
        return [] if value is None else value


class ApiResult(BaseModel):
    operation_id: str
    ok: bool
    status_code: int | None = None
    method: str
    path: str
    request: dict[str, Any] = Field(default_factory=dict)
    data: Any = None
    error: Any = None
    response_validation_warnings: list[str] = Field(default_factory=list)
