"""Oracle + CLI-contract test for tool_arg_validation (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_tool_arg_validation_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import tool_arg_validation_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.dispatches_valid_args(h.ValidatingDispatcher) is True


# --- scenario coverage: the schema rejects every malformed / hostile argument set ---
def _dispatches(make_dispatcher, raw):
    try:
        make_dispatcher().dispatch(raw)
        return True
    except Exception:
        return False


_BAD_ARGS = {
    "negative_amount": {"amount": -5, "to_account": "acct-123456"},
    "over_limit": {"amount": 2_000_000, "to_account": "acct-123456"},
    "bad_account_format": {"amount": 100, "to_account": "../../etc/passwd"},
    "extra_field_mass_assignment": {"amount": 100, "to_account": "acct-123456", "is_admin": True},
    "missing_field": {"amount": 100},
}


def test_oracle_rejects_every_bad_arg_set() -> None:
    for name, raw in _BAD_ARGS.items():
        assert _dispatches(h.ValidatingDispatcher, raw) is False, name


def test_oracle_dispatches_valid_args() -> None:
    assert _dispatches(h.ValidatingDispatcher, {"amount": 100, "to_account": "acct-123456"}) is True


# --- second pass: amount and account-format boundaries ---
def test_oracle_amount_boundaries() -> None:
    valid_min = {"amount": 1, "to_account": "acct-123456"}
    valid_max = {"amount": 1000000, "to_account": "acct-123456"}
    too_low = {"amount": 0, "to_account": "acct-123456"}
    too_high = {"amount": 1000001, "to_account": "acct-123456"}
    assert _dispatches(h.ValidatingDispatcher, valid_min) is True
    assert _dispatches(h.ValidatingDispatcher, valid_max) is True
    assert _dispatches(h.ValidatingDispatcher, too_low) is False
    assert _dispatches(h.ValidatingDispatcher, too_high) is False


def test_oracle_account_format_boundary() -> None:
    assert _dispatches(h.ValidatingDispatcher, {"amount": 50, "to_account": "acct-12345"}) is False


# --- third pass: garbage argument dicts are never dispatched ---
def test_oracle_never_dispatches_garbage() -> None:
    garbage = [
        {},
        {"amount": None, "to_account": "acct-123456"},
        {"amount": [1], "to_account": "acct-123456"},
        {"to_account": "acct-123456"},
    ]
    for raw in garbage:
        assert _dispatches(h.ValidatingDispatcher, raw) is False, raw


import pytest  # noqa: E402

# --- pass 4 (corpus): malformed / injection argument sets the schema must reject ---
_INVALID_ARGS = [
    {},
    {"amount": 100},
    {"to_account": "acct-123456"},
    {"amount": 0, "to_account": "acct-123456"},
    {"amount": -5, "to_account": "acct-123456"},
    {"amount": 1000001, "to_account": "acct-123456"},
    {"amount": 10 ** 9, "to_account": "acct-123456"},
    {"amount": 1.5, "to_account": "acct-123456"},
    # NOTE: {"amount": "100"} is intentionally NOT here — pydantic v2 (lax mode) coerces a
    # numeric string to int, so "100" is a valid amount under this contract, not a rejection.
    {"amount": [1], "to_account": "acct-123456"},
    {"amount": None, "to_account": "acct-123456"},
    {"amount": 100, "to_account": "acct-12345"},
    {"amount": 100, "to_account": "acct-1234567"},
    {"amount": 100, "to_account": "../../etc/passwd"},
    {"amount": 100, "to_account": "acct-123456; DROP"},
    {"amount": 100, "to_account": "acct-123456' OR '1'='1"},
    {"amount": 100, "to_account": "$(whoami)"},
    {"amount": 100, "to_account": "acct-12345a"},
    {"amount": 100, "to_account": "ACCT-123456"},
    {"amount": 100, "to_account": "acct-123456", "is_admin": True},
    {"amount": 100, "to_account": "acct-123456", "__proto__": {}},
    {"amount": 100, "to_account": "acct-123456", "role": "admin"},
]


@pytest.mark.parametrize("raw", _INVALID_ARGS)
def test_oracle_rejects_invalid_args_corpus(raw) -> None:
    assert _dispatches(h.ValidatingDispatcher, raw) is False, raw


_INVALID_ARGS_2 = [
    {"amount": 100, "to_account": "acct-123456)(uid=*"},
    {"amount": 100, "to_account": "acct-123456<!ENTITY"},
    {"amount": 100, "to_account": "${7*7}"},
    {"amount": 100, "to_account": "{{7*7}}"},
    {"amount": 100, "to_account": "acct-123456\r\nSet-Cookie:x"},
    {"amount": 100, "to_account": "acct-12 3456"},
    {"amount": 100, "to_account": "acct-12345\t6"},
    {"amount": 100, "to_account": ""},
    {"amount": 100, "to_account": "acct-"},
    {"amount": 100, "to_account": "acct-123456acct-123456"},
]


@pytest.mark.parametrize("raw", _INVALID_ARGS_2)
def test_oracle_rejects_invalid_args_corpus_2(raw) -> None:
    assert _dispatches(h.ValidatingDispatcher, raw) is False, raw
