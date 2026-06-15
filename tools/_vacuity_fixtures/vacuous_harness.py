"""A deliberately VACUOUS harness fixture: its self-test passes without ever depending on the
oracle's correctness, so neutering the oracle does NOT turn it red. The vacuity gate must
detect this and classify it as VACUOUS — that is the failure mode the gate exists to catch."""

VACUITY_TARGETS = ["oracle"]


def oracle(value: int) -> int:
    return abs(value)


def buggy(value: int) -> int:
    return value


def run_self_test() -> int:
    # VACUOUS GREEN: asserts something trivially true and never checks the oracle.
    return 0 if isinstance(oracle, object) else 1
