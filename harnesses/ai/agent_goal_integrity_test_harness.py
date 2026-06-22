#!/usr/bin/env python3
"""Agent goal/plan-conformance harness (Hypothesis).

OWASP Top 10 for Agentic Applications 2026 -- ASI01 Agent Goal Hijack.

WHY: Goal hijack is "prompt injection with action consequences" -- a malicious instruction
hidden in data the agent processes (an email, a document, a tool result) redirects the
agent into executing an UNPLANNED, often irreversible step. A test that runs the agent's
happy-path plan passes whether or not unplanned steps are blocked; only checking that NO
step outside the approved plan can execute exposes the hijack. The 2026 mitigation is a
plan-validation checkpoint -- the agent may only run steps that belong to its declared goal.

HOW: `PlanConformantAgent` is the ORACLE -- `execute_step` refuses any step not in the
approved plan. `FreeReasoningAgent` is the planted defect -- it runs whatever the
(hijackable) reasoning proposes. `find_unplanned_execution` runs a Hypothesis property
("no step outside the plan executes") over a mix of planned steps and injected irreversible
ones, and returns True when falsified: the oracle holds, the free agent is falsified.

WHERE: ai/ -- in-process, deterministic. Adds `hypothesis` to the `ai` extra (already in the repo).

Self-test:
    python harnesses/ai/agent_goal_integrity_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys

from hypothesis import given, settings
from hypothesis import strategies as st

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["PlanConformantAgent.execute_step"]

DOSSIER = {
    "name": "agent_goal_integrity",
    "path": "harnesses/ai/agent_goal_integrity_test_harness.py",
    "flavor": "ai",
    "dependency": "hypothesis",
    "standard": "OWASP Top 10 for Agentic Applications 2026 - ASI01 Agent Goal Hijack",
    "failure_class": (
        "An injected instruction redirects the agent into an unplanned/irreversible step"
    ),
    "oracle": "PlanConformantAgent.execute_step - refuse any step not in the approved plan",
    "buggy": "FreeReasoningAgent.execute_step - run whatever the reasoning proposes",
    "planted_mutant": (
        "Hypothesis injects an irreversible step (delete_database/...) the free agent runs"
    ),
    "proof_file": "tests/ai/test_agent_goal_integrity_proof.py",
    "vacuity_targets": ["PlanConformantAgent.execute_step"],
    "commands": ["python harnesses/ai/agent_goal_integrity_test_harness.py --self-test"],
    "known_limits": (
        "checks plan membership; full defence also needs loop caps + irreversible-action gates"
    ),
    "related": ["agent_memory_trust (ASI06)", "agent_human_confirmation (ASI09)"],
}

APPROVED_PLAN = ["fetch_data", "summarize", "send_report"]
_INJECTED = ["delete_database", "wire_funds", "exfiltrate_secrets", "disable_logging"]


class PlanConformantAgent:
    """ORACLE: only steps in the approved plan may execute."""

    def execute_step(self, step: str) -> str:
        if step not in APPROVED_PLAN:
            raise PermissionError(f"step '{step}' is not in the approved plan (goal hijack)")
        return f"ran:{step}"


class FreeReasoningAgent:
    """BUGGY: run whatever step the (hijackable) reasoning proposes."""

    def execute_step(self, step: str) -> str:
        return f"ran:{step}"  # BUG: no plan validation


def runs_planned_step(agent) -> bool:
    return agent.execute_step("summarize") == "ran:summarize"


def find_unplanned_execution(agent) -> bool:
    """True == Hypothesis found a step outside the plan that executed (goal hijack)."""
    @settings(max_examples=200)
    @given(step=st.sampled_from(APPROVED_PLAN + _INJECTED))
    def prop(step: str) -> None:
        if step not in APPROVED_PLAN:
            try:
                agent.execute_step(step)
            except PermissionError:
                return
            raise AssertionError(f"executed unplanned step: {step}")

    try:
        prop()
    except AssertionError:
        return True
    return False


def run_self_test() -> int:
    failures = 0
    if not runs_planned_step(PlanConformantAgent()):
        failures += 1
        print("FAIL: oracle refused a step that is in the approved plan", file=sys.stderr)
    if find_unplanned_execution(PlanConformantAgent()):
        failures += 1
        print("FAIL: oracle executed a step outside the approved plan", file=sys.stderr)
    if not find_unplanned_execution(FreeReasoningAgent()):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: free-reasoning agent goal hijack was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(
        "self-test: OK (plan-conformant agent blocks unplanned steps; free agent caught by "
        "Hypothesis)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent goal/plan-conformance harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
