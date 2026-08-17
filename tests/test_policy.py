from conversational_agent.policy import approved, confirmation_required


def test_confirmation_parser_accepts_explicit_approval():
    assert approved("yes") is True
    assert approved("approve") is True
    assert approved({"decision": "proceed"}) is True
    assert approved(True) is True


def test_confirmation_parser_rejects_nonapproval():
    assert approved("no") is False
    assert approved({"decision": "reject"}) is False
    assert approved(False) is False
    assert approved(None) is False


def test_required_confirmation_is_always_required():
    operation = {"execution": {"confirmation": "required"}}
    assert confirmation_required(operation, inferred_fields=[], confidence=1.0) is True


def test_conditional_confirmation_tracks_inference_and_confidence():
    operation = {"execution": {"confirmation": "conditional"}}
    assert confirmation_required(operation, inferred_fields=[], confidence=0.95) is False
    assert confirmation_required(operation, inferred_fields=["order_id"], confidence=0.95) is True
    assert confirmation_required(operation, inferred_fields=[], confidence=0.7) is True


def test_never_confirmation_does_not_interrupt():
    operation = {"execution": {"confirmation": "never"}}
    assert confirmation_required(operation, inferred_fields=["order_id"], confidence=0.1) is False
