"""Proof: a circuit breaker bounds the cascade the no-breaker orchestrator suffers. Fanning
out 100 tasks at a dead dependency, the no-breaker orchestrator makes far more than the
threshold of calls; the breaker-isolated one does not."""

from harnesses.ai import agent_circuit_breaker_test_harness as h


def test_proof_no_breaker_cascades() -> None:
    assert h.cascades_on_failure(h.NoBreakerOrchestrator) is True


def test_proof_breaker_isolates() -> None:
    assert h.cascades_on_failure(h.IsolatedOrchestrator) is False


# --- scenario coverage: with no breaker every fanned-out task hits the dead dependency ---
def test_proof_no_breaker_cascades_to_all_tasks() -> None:
    assert h.NoBreakerOrchestrator().fan_out(h.FAN_OUT) == h.FAN_OUT
    assert h.cascades_on_failure(h.NoBreakerOrchestrator) is True
