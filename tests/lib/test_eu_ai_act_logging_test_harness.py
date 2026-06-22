"""Oracle + CLI-contract test for eu_ai_act_logging (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_eu_ai_act_logging_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import eu_ai_act_logging_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.records_complete_event(h.CompliantLogger) is True


# --- scenario coverage: the compliant logger rejects every incomplete / ill-typed event ---
_COMPLETE_EVENT = {"timestamp": 1.0, "input_ref": "req-1", "result": "deny", "operator": "system"}


def _logger_accepts(make_logger, event):
    try:
        make_logger().record(event)
        return True
    except Exception:
        return False


def test_oracle_rejects_each_missing_required_field() -> None:
    for field in ("timestamp", "input_ref", "result", "operator"):
        event = {k: v for k, v in _COMPLETE_EVENT.items() if k != field}
        assert _logger_accepts(h.CompliantLogger, event) is False, field


def test_oracle_rejects_wrong_typed_field() -> None:
    event = dict(_COMPLETE_EVENT, timestamp="not-a-number")
    assert _logger_accepts(h.CompliantLogger, event) is False


def test_oracle_accepts_complete_event() -> None:
    assert _logger_accepts(h.CompliantLogger, _COMPLETE_EVENT) is True


# --- second pass: a complete event with extra fields is still accepted ---
def test_oracle_accepts_event_with_extra_fields() -> None:
    event = dict(_COMPLETE_EVENT, request_id="r-9", latency_ms=12)
    assert _logger_accepts(h.CompliantLogger, event) is True


# --- third pass: garbage / wrong-typed events are never recorded ---
def test_oracle_never_records_garbage_events() -> None:
    bad = [
        {},
        {"timestamp": 1.0},
        {"foo": "bar"},
        {"timestamp": "x", "input_ref": "r", "result": "d", "operator": "o"},
    ]
    for event in bad:
        assert _logger_accepts(h.CompliantLogger, event) is False, event


import pytest  # noqa: E402


@pytest.mark.parametrize("event", [
    {},
    {"timestamp": 1.0},
    {"timestamp": 1.0, "input_ref": "r"},
    {"timestamp": 1.0, "input_ref": "r", "result": "d"},
    {"input_ref": "r", "result": "d", "operator": "o"},
    {"timestamp": "x", "input_ref": "r", "result": "d", "operator": "o"},
    {"timestamp": 1.0, "input_ref": 1, "result": "d", "operator": "o"},
    {"timestamp": 1.0, "input_ref": "r", "result": 2, "operator": "o"},
    {"timestamp": 1.0, "input_ref": "r", "result": "d", "operator": None},
])
def test_oracle_rejects_noncompliant_event(event) -> None:
    assert _logger_accepts(h.CompliantLogger, event) is False, event
