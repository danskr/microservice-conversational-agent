from pathlib import Path

import httpx
import pytest

from conversational_agent.digest import DigestStore
from conversational_agent.executor import DeterministicRestExecutor
from conversational_agent.models import PendingCall
from conversational_agent.validation import OperationValidator


DIGEST = Path(__file__).parents[1] / "digest" / "order-fulfillment-service-digest.yaml"


class _FakeAsyncClient:
    last_method = None
    last_url = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, **kwargs):
        type(self).last_method = method
        type(self).last_url = url
        return httpx.Response(
            200,
            json={
                "id": "ORD-123",
                "customer_id": "CUS-1",
                "status": "DRAFT",
                "payment_status": "NONE",
                "currency": "USD",
                "shipping_address": "123 Test Street",
                "total_amount": "0.00",
                "created_at": "2026-08-13T00:00:00Z",
                "updated_at": "2026-08-13T00:00:00Z",
                "items": [],
            },
        )


@pytest.mark.asyncio
async def test_executor_uses_digest_method_and_path(monkeypatch):
    store = DigestStore(DIGEST)
    validator = OperationValidator(store)
    executor = DeterministicRestExecutor(store, validator)
    executor.settings.order_service_base_url = "http://orders.test"
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    result = await executor.execute(PendingCall(operation_id="get_order", path_params={"order_id": "ORD-123"}))
    assert result.ok is True
    assert result.method == "GET"
    assert result.path == "/orders/ORD-123"
    assert _FakeAsyncClient.last_method == "GET"
    assert _FakeAsyncClient.last_url == "http://orders.test/orders/ORD-123"


@pytest.mark.asyncio
async def test_executor_blocks_unknown_operation():
    store = DigestStore(DIGEST)
    validator = OperationValidator(store)
    executor = DeterministicRestExecutor(store, validator)
    result = await executor.execute(PendingCall(operation_id="delete_everything"))
    assert result.ok is False
    assert result.method == "BLOCKED"
    assert result.error["code"] == "UNKNOWN_OPERATION"
