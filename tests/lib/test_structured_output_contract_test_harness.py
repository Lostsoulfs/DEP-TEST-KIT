"""Oracle + CLI-contract test for structured_output_contract (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_structured_output_contract_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import structured_output_contract_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.executes_valid_output(h.ValidatingExecutor) is True


# --- scenario coverage: the schema rejects every malformed model output ---
_VALID_OUTPUT = {"tool": "transfer", "amount": 100, "to": "acct-123456"}


def _executes(make_executor, output):
    try:
        make_executor().execute(output)
        return True
    except Exception:
        return False


_MALFORMED = {
    "negative_amount": {**_VALID_OUTPUT, "amount": -5},
    "bad_account": {**_VALID_OUTPUT, "to": "../etc/passwd"},
    "extra_field": {**_VALID_OUTPUT, "role": "admin"},
    "missing_tool": {"amount": 100, "to": "acct-123456"},
    "wrong_type": {**_VALID_OUTPUT, "amount": "lots"},
}


def test_oracle_executes_valid_output() -> None:
    assert _executes(h.ValidatingExecutor, _VALID_OUTPUT) is True


def test_oracle_rejects_every_malformed_output() -> None:
    for name, output in _MALFORMED.items():
        assert _executes(h.ValidatingExecutor, output) is False, name


# --- second pass: more malformed outputs rejected; a valid one still executes ---
def test_oracle_rejects_more_malformed_outputs() -> None:
    bad = [
        {"tool": "transfer", "amount": 100},                       # missing 'to'
        {"tool": "transfer", "amount": 1.5, "to": "acct-123456"},  # non-integer amount
        {"tool": "transfer", "amount": "100", "to": "acct-123456"},  # string amount
    ]
    for output in bad:
        assert _executes(h.ValidatingExecutor, output) is False, output


def test_oracle_executes_another_valid_output() -> None:
    valid = {"tool": "transfer", "amount": 100, "to": "acct-654321"}
    assert _executes(h.ValidatingExecutor, valid) is True


# --- third pass: garbage / incomplete outputs are never executed ---
def test_oracle_never_executes_garbage_outputs() -> None:
    bad = [{}, {"tool": "transfer"}, {"amount": 100}, {"tool": "x", "amount": 1, "to": "y"}]
    for output in bad:
        assert _executes(h.ValidatingExecutor, output) is False, output


import pytest  # noqa: E402

# --- pass 4 (researched corpus): malformed LLM tool-call outputs the schema must reject ---
_BASE = {"tool": "transfer", "amount": 100, "to": "acct-123456"}
_MALFORMED_CORPUS = [
    ("negative_amount", {**_BASE, "amount": -5}),
    ("zero_amount", {**_BASE, "amount": 0}),
    ("over_max_amount", {**_BASE, "amount": 10 ** 9}),
    ("float_amount", {**_BASE, "amount": 1.5}),
    ("string_amount", {**_BASE, "amount": "100"}),
    ("array_amount", {**_BASE, "amount": [100]}),
    ("null_amount", {**_BASE, "amount": None}),
    ("path_traversal_to", {**_BASE, "to": "../etc/passwd"}),
    ("short_account", {**_BASE, "to": "acct-12345"}),
    ("sqli_to", {**_BASE, "to": "acct-1; DROP"}),
    ("extra_field", {**_BASE, "role": "admin"}),
    ("extra_nested", {**_BASE, "meta": {"x": 1}}),
    ("bad_tool_enum", {**_BASE, "tool": "exfiltrate"}),
    ("missing_tool", {"amount": 100, "to": "acct-123456"}),
    ("missing_amount", {"tool": "transfer", "to": "acct-123456"}),
    ("missing_to", {"tool": "transfer", "amount": 100}),
    ("empty", {}),
]


@pytest.mark.parametrize("name,output", _MALFORMED_CORPUS)
def test_oracle_rejects_malformed_output(name, output) -> None:
    assert _executes(h.ValidatingExecutor, output) is False, name


@pytest.mark.parametrize("output", [
    {"tool": "transfer", "amount": 1, "to": "acct-000000"},
    {"tool": "transfer", "amount": 1000000, "to": "acct-999999"},
    {"tool": "transfer", "amount": 500, "to": "acct-123456"},
    {"tool": "transfer", "amount": 42, "to": "acct-654321"},
    {"tool": "transfer", "amount": 999999, "to": "acct-111111"},
])
def test_oracle_accepts_valid_output_corpus(output) -> None:
    assert _executes(h.ValidatingExecutor, output) is True, output


# === our own / batch 5 (original; math bench) ===
# Adeyemi (whimsical/psych) + math: the amount fence is [1, 1_000_000]; a bool is NOT an integer
# to jsonschema, so amount=True is rejected (no type-juggling into the allowed range).
def test_oracle_amount_boundary_and_bool_not_integer() -> None:
    def accepts(amount):
        try:
            h.ValidatingExecutor().execute(
                {"tool": "transfer", "amount": amount, "to": "acct-123456"})
            return True
        except Exception:
            return False
    assert accepts(1) and accepts(1_000_000)
    assert not accepts(0) and not accepts(1_000_001) and not accepts(True)
