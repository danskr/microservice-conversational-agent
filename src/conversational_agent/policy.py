from __future__ import annotations

from typing import Any


def confirmation_required(
    operation: dict[str, Any],
    *,
    inferred_fields: list[str],
    confidence: float,
    confirm_conditional_actions: bool = False,
) -> bool:
    """Apply the digest's never/conditional/required confirmation semantics."""
    confirmation = operation.get("execution", {}).get("confirmation", "required")
    if confirmation == "required":
        return True
    if confirmation == "conditional":
        return confirm_conditional_actions or bool(inferred_fields) or confidence < 0.9
    return False


def approved(value: Any) -> bool:
    """Parse an interrupt resume value conservatively; unknown values are rejection."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {
            "yes",
            "y",
            "approve",
            "approved",
            "proceed",
            "confirm",
            "confirmed",
        }
    if isinstance(value, dict):
        raw = value.get("decision", value.get("action", value.get("approved")))
        return approved(raw)
    return False
