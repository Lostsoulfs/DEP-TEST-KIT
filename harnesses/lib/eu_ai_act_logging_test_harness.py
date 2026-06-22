#!/usr/bin/env python3
"""EU AI Act Article 12 event-logging completeness harness (jsonschema).

EU AI Act (Regulation 2024/1689) Article 12 -- automatic record-keeping for high-risk AI
systems (full application 2 Aug 2026; non-compliance up to EUR 15M or 3% of turnover).

WHY: Article 12 requires high-risk AI systems to AUTOMATICALLY log events traceably over
their lifetime -- each record carrying enough context to reconstruct what happened (time,
the input/reference data, the result, the responsible operator). A logger that "writes a
line" passes a test that only checks a log was emitted; the compliance gap shows when a
record is MISSING required fields. A schema check over each event catches it.

HOW: `CompliantLogger` is the ORACLE -- it validates every event against the Article-12
minimum-field schema before recording, rejecting an incomplete record. `LossyLogger` is the
planted defect -- it records whatever it is handed. `accepts_incomplete_event` submits a
record missing the input reference, result, and operator: the oracle rejects, the lossy
logger stores it.

WHERE: lib/ -- dependency-backed (`jsonschema`) but in-process, no service. Adds `jsonschema`
to the `lib` extra.

Self-test:
    python harnesses/lib/eu_ai_act_logging_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from jsonschema import validate

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_incomplete_event"]

DOSSIER = {
    "name": "eu_ai_act_logging",
    "path": "harnesses/lib/eu_ai_act_logging_test_harness.py",
    "flavor": "lib",
    "dependency": "jsonschema",
    "standard": (
        "EU AI Act (Reg 2024/1689) Article 12 - automatic event logging (high-risk, 2 Aug 2026)"
    ),
    "failure_class": (
        "Recording an audit event missing the Article-12 minimum fields (not traceable)"
    ),
    "oracle": "CompliantLogger.record - validate each event against the Article-12 field schema",
    "buggy": "LossyLogger.record - store whatever is handed in",
    "planted_mutant": "submit an event missing input_ref/result/operator; lossy logger stores it",
    "proof_file": "tests/lib/test_eu_ai_act_logging_proof.py",
    "vacuity_targets": ["accepts_incomplete_event"],
    "commands": ["python harnesses/lib/eu_ai_act_logging_test_harness.py --self-test"],
    "known_limits": (
        "field-completeness only; no finalized Art.12 standard yet (prEN 18229-1 / ISO DIS 24970 "
        "drafts)"
    ),
    "related": ["security_logging (audit coverage)", "provenance_attestation"],
}

# Article-12 minimum context per recorded event (timestamp, input reference, result, operator).
EVENT_SCHEMA = {
    "type": "object",
    "required": ["timestamp", "input_ref", "result", "operator"],
    "properties": {
        "timestamp": {"type": "number"},
        "input_ref": {"type": "string"},
        "result": {"type": "string"},
        "operator": {"type": "string"},
    },
}


class CompliantLogger:
    """ORACLE: validate every event against the Article-12 schema before recording."""

    def __init__(self) -> None:
        self._log: list = []

    def record(self, event: dict) -> None:
        validate(instance=event, schema=EVENT_SCHEMA)  # raises if a required field is missing
        self._log.append(event)


class LossyLogger:
    """BUGGY: store whatever is handed in -- incomplete events included."""

    def __init__(self) -> None:
        self._log: list = []

    def record(self, event: dict) -> None:
        self._log.append(event)  # BUG: no completeness check


def records_complete_event(make_logger: Callable[[], object]) -> bool:
    good = {"timestamp": 1.0, "input_ref": "req-1", "result": "deny", "operator": "system"}
    try:
        make_logger().record(good)
        return True
    except Exception:
        return False


def accepts_incomplete_event(make_logger: Callable[[], object]) -> bool:
    """True == a non-compliant (incomplete) event was recorded (the bug); False == rejected."""
    incomplete = {"timestamp": 1.0}  # missing input_ref, result, operator
    try:
        make_logger().record(incomplete)
        return True
    except Exception:
        return False


def run_self_test() -> int:
    failures = 0
    if not records_complete_event(CompliantLogger):
        failures += 1
        print("FAIL: oracle rejected a complete, compliant event", file=sys.stderr)
    if accepts_incomplete_event(CompliantLogger):
        failures += 1
        print("FAIL: oracle recorded an incomplete event", file=sys.stderr)
    if not accepts_incomplete_event(LossyLogger):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: lossy logger was NOT caught recording an incomplete event", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (compliant logger rejects incomplete events; lossy logger caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EU AI Act Article 12 logging-completeness harness"
    )
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
