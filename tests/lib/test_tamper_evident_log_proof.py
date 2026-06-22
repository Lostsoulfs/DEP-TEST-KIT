"""Proof: the HMAC hash-chain detects the rewritten entry the plain log accepts.
verify() breaks on tamper vs always returning True."""

from harnesses.lib import tamper_evident_log_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.tampering_undetected(h.PlainLog) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.tampering_undetected(h.HashChainedLog) is False


def test_proof_oracle_happy_path() -> None:
    assert h.intact_log_verifies(h.HashChainedLog) is True


# --- scenario coverage: the plain log misses every tampering mode ---
def _plain(entries):
    log = h.PlainLog()
    for entry in entries:
        log.append(entry)
    return log


def test_proof_plain_log_misses_edit() -> None:
    log = _plain(["a", "b", "c"])
    log.tamper(1, "X")
    assert log.verify() is True


def test_proof_plain_log_misses_delete() -> None:
    log = _plain(["a", "b", "c"])
    del log._entries[1]
    assert log.verify() is True


def test_proof_plain_log_misses_reorder() -> None:
    log = _plain(["a", "b", "c"])
    log._entries[1], log._entries[2] = log._entries[2], log._entries[1]
    assert log.verify() is True
