from pathlib import Path

from conversational_agent.digest import DigestStore
from conversational_agent.models import PendingCall
from conversational_agent.validation import OperationValidator


DIGEST = Path(__file__).parents[1] / "digest" / "order-fulfillment-service-digest.yaml"


def _validator():
    store = DigestStore(DIGEST)
    return OperationValidator(store)


def test_cancel_requires_order_id_and_body():
    validator = _validator()
    call = PendingCall(operation_id="cancel_order")
    issues = validator.validate_call(call)
    assert any("order_id" in issue for issue in issues)
    assert any("request body" in issue.lower() for issue in issues)


def test_valid_cancel_call_passes_schema_validation():
    validator = _validator()
    call = PendingCall(
        operation_id="cancel_order",
        path_params={"order_id": "ORD-TEST"},
        body={"reason": "Customer changed mind"},
    )
    assert validator.validate_call(call) == []


def test_list_orders_rejects_unknown_query_parameter():
    validator = _validator()
    call = PendingCall(operation_id="list_orders", query_params={"not_a_real_filter": "x"})
    issues = validator.validate_call(call)
    assert any("Unexpected query" in issue for issue in issues)
