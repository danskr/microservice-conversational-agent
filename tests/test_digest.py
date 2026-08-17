from pathlib import Path

from conversational_agent.digest import DigestStore


DIGEST = Path(__file__).parents[1] / "digest" / "order-fulfillment-service-digest.yaml"


def test_digest_loads_and_has_all_operations():
    store = DigestStore(DIGEST)
    assert store.data["agent_index"]["operation_count"] == 30
    assert len(store.operations) == 30
    assert "cancel_order" in store.operations
    assert store.operations["cancel_order"]["execution"]["confirmation"] == "required"


def test_digest_search_finds_cancellation_semantics():
    store = DigestStore(DIGEST)
    hits = store.search("when can I cancel an order after shipping", limit=8)
    keys = {hit.key for hit in hits}
    assert "cancel_order" in keys or "BR-CANCEL-001" in keys


def test_catalog_contains_only_digest_operations():
    store = DigestStore(DIGEST)
    ids = {item["operation_id"] for item in store.compact_operation_catalog()}
    assert ids == set(store.operations)
