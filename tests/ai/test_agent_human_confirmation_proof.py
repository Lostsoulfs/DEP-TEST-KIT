"""Proof: out-of-band step-up stops the self-asserted consent the in-band executor accepts.
The in-band executor runs an irreversible action with no human signature; the step-up
executor refuses it."""

from harnesses.ai import agent_human_confirmation_test_harness as h


def test_proof_inband_executor_caught_by_detector() -> None:
    assert h.executes_without_stepup(h.InBandConsentExecutor) is True


def test_proof_stepup_executor_refuses_without_stepup() -> None:
    assert h.executes_without_stepup(h.StepUpExecutor) is False


def test_proof_stepup_executor_runs_with_valid_stepup() -> None:
    assert h.executes_with_valid_stepup(h.StepUpExecutor) is True


# --- scenario coverage: the in-band executor runs irreversible actions with no step-up ---
def test_proof_inband_executor_runs_without_stepup() -> None:
    executor = h.InBandConsentExecutor()
    assert executor.execute("wire_transfer", "n-1", None) == "executed:wire_transfer"
    assert executor.execute("refund_all", "n-9", b"\x00" * 64) == "executed:refund_all"
