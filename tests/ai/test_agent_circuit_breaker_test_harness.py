"""Oracle + CLI-contract test for agent_circuit_breaker (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_agent_circuit_breaker_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.ai import agent_circuit_breaker_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_secure_path() -> None:
    assert h.cascades_on_failure(h.IsolatedOrchestrator) is False


# --- scenario coverage: the breaker caps calls to a dead dependency ---
def test_oracle_caps_calls_to_failing_dependency() -> None:
    calls = h.IsolatedOrchestrator().fan_out(h.FAN_OUT)
    assert calls <= h.CASCADE_THRESHOLD


def test_oracle_does_not_cascade() -> None:
    assert h.cascades_on_failure(h.IsolatedOrchestrator) is False


# --- second pass: the breaker short-circuits well below the fan-out ---
def test_oracle_short_circuits_below_fanout() -> None:
    calls = h.IsolatedOrchestrator().fan_out(h.FAN_OUT)
    assert calls < h.FAN_OUT
    assert calls <= 3


# --- third pass: the fan-out cap is consistent across runs ---
def test_oracle_fanout_cap_is_consistent() -> None:
    assert h.IsolatedOrchestrator().fan_out(h.FAN_OUT) <= 3
    assert h.IsolatedOrchestrator().fan_out(h.FAN_OUT) <= 3


import pytest  # noqa: E402


@pytest.mark.parametrize("fanout", [3, 5, 10, 20, 50])
def test_oracle_caps_calls_regardless_of_fanout(fanout) -> None:
    assert h.IsolatedOrchestrator().fan_out(fanout) <= 3, fanout
