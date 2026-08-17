from conversational_agent.entities import extract_active_entities


def test_extracts_canonical_id_prefixes():
    data = {
        "id": "ORD-ABC",
        "items": [{"id": "ITM-1"}],
        "refund": {"id": "RFD-9"},
    }
    found = extract_active_entities(data)
    assert found["order_id"] == "ORD-ABC"
    assert found["order_item_id"] == "ITM-1"
    assert found["refund_id"] == "RFD-9"


def test_newest_first_list_keeps_first_order_active():
    data = [{"id": "ORD-NEW"}, {"id": "ORD-OLD"}]
    found = extract_active_entities(data)
    assert found["order_id"] == "ORD-NEW"
