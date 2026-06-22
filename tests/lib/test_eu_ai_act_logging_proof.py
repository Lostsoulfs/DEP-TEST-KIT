"""Proof: schema validation rejects the incomplete event the lossy logger stores. The lossy
logger records an event missing required Article-12 fields; the compliant logger rejects it."""

from harnesses.lib import eu_ai_act_logging_test_harness as h


def test_proof_lossy_logger_accepts_incomplete() -> None:
    assert h.accepts_incomplete_event(h.LossyLogger) is True


def test_proof_compliant_logger_rejects_incomplete() -> None:
    assert h.accepts_incomplete_event(h.CompliantLogger) is False


def test_proof_compliant_logger_records_complete() -> None:
    assert h.records_complete_event(h.CompliantLogger) is True


# --- scenario coverage: the lossy logger stores every malformed event ---
def _lossy_accepts(event):
    try:
        h.LossyLogger().record(event)
        return True
    except Exception:
        return False


def test_proof_lossy_stores_every_incomplete_event() -> None:
    complete = {"timestamp": 1.0, "input_ref": "r", "result": "deny", "operator": "sys"}
    for field in complete:
        event = {k: v for k, v in complete.items() if k != field}
        assert _lossy_accepts(event) is True, field
