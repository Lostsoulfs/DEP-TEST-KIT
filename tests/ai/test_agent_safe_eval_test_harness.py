"""Oracle + CLI-contract test for agent_safe_eval (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_agent_safe_eval_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.ai import agent_safe_eval_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.evaluates_safe_math(h.SafeEvaluator) is True


# --- scenario coverage: benign math evaluates; attribute escapes are refused ---
_ESCAPES = ["().__class__", "(1).__class__.__bases__", "[].__class__.__mro__"]


def test_oracle_evaluates_benign_math() -> None:
    evaluator = h.SafeEvaluator()
    assert evaluator.eval("2 + 3 * 4") == 14
    assert evaluator.eval("100 - 58") == 42


def test_oracle_refuses_attribute_escapes() -> None:
    evaluator = h.SafeEvaluator()
    for probe in _ESCAPES:
        try:
            evaluator.eval(probe)
            ran = True
        except Exception:
            ran = False
        assert ran is False, probe


# --- second pass: richer benign math; more escape probes refused ---
def test_oracle_evaluates_more_benign_expressions() -> None:
    evaluator = h.SafeEvaluator()
    assert evaluator.eval("(2 + 3) * (4 - 1)") == 15
    assert evaluator.eval("10 % 3") == 1


def test_oracle_refuses_more_escape_probes() -> None:
    evaluator = h.SafeEvaluator()
    for probe in ("__import__('os')", "().__class__.__bases__", "(1).__class__"):
        try:
            evaluator.eval(probe)
            ran = True
        except Exception:
            ran = False
        assert ran is False, probe


# --- third pass: garbage expressions raise rather than silently evaluating ---
def test_oracle_garbage_expressions_raise() -> None:
    evaluator = h.SafeEvaluator()
    for expr in ["1 +", "][", "import os"]:
        try:
            evaluator.eval(expr)
            raised = False
        except Exception:
            raised = True
        assert raised is True, expr


import pytest  # noqa: E402

# --- pass 4 (corpus): simpleeval blocks attribute access + undefined names ---
# NOTE: simpleeval allows a bare non-dunder method *reference* like "''.join" (it returns
# the bound method, harmless without a call), so that is not an escape and is intentionally
# excluded. The dangerous surface — dunder traversal, DISALLOW_METHODS (format), and
# undefined builtins (open/exec/__import__) — is what must be refused.
_EVAL_ESCAPES = [
    "().__class__", "(1).__class__", "[].__class__", "''.__class__", "{}.__class__",
    "().__class__.__bases__", "''.__class__.__mro__", "().__class__.__subclasses__()",
    "''.format", "[].append",
    "__import__('os')", "__import__('subprocess')", "open('/etc/passwd')",
    "exec('x=1')", "eval('1+1')", "globals()", "locals()", "vars()", "dir()",
    "getattr([], 'append')", "compile('1', 'x', 'eval')", "os.system('id')",
    "open", "__builtins__",
]


@pytest.mark.parametrize("expr", _EVAL_ESCAPES)
def test_oracle_refuses_eval_escape(expr) -> None:
    try:
        h.SafeEvaluator().eval(expr)
        ran = True
    except Exception:
        ran = False
    assert ran is False, expr


_BENIGN_MATH = [
    ("2+3", 5), ("10-4", 6), ("3*4", 12), ("20/5", 4), ("2**8", 256),
    ("17%5", 2), ("(2+3)*4", 20), ("100//7", 14), ("1+2+3+4", 10), ("9-3*2", 3),
]


@pytest.mark.parametrize("expr,expected", _BENIGN_MATH)
def test_oracle_evaluates_benign_math_corpus(expr, expected) -> None:
    assert h.SafeEvaluator().eval(expr) == expected, expr
