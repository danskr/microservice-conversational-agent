from __future__ import annotations

from typing import Any


_PREFIX_ENTITY = {
    "ORD-": "order_id",
    "CUS-": "customer_id",
    "ITM-": "order_item_id",
    "SHP-": "shipment_id",
    "RET-": "return_id",
    "RSV-": "reservation_id",
    "SIT-": "shipment_item_id",
    "RIT-": "return_item_id",
    "RFD-": "refund_id",
    "EVT-": "event_id",
}


def extract_active_entities(data: Any) -> dict[str, str]:
    """Extract recent concrete entity IDs from an API result for conversational references."""
    found: dict[str, str] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            # Prefer explicit semantic fields where available.
            for field in (
                "order_id",
                "customer_id",
                "order_item_id",
                "shipment_id",
                "return_id",
                "refund_id",
                "sku",
            ):
                if field in value and isinstance(value[field], str):
                    found[field] = value[field]
            for key, child in value.items():
                if key == "id" and isinstance(child, str):
                    for prefix, entity_name in _PREFIX_ENTITY.items():
                        if child.startswith(prefix):
                            found[entity_name] = child
                            break
                visit(child)
        elif isinstance(value, list):
            # Lists are usually newest-first in this service. Traverse reversed so the
            # first item ends up as the active entity after later assignments.
            for child in reversed(value):
                visit(child)

    visit(data)
    return found
