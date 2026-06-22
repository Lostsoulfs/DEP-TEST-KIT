"""Proof: the real Jinja2 sandbox refuses the escape a plain Environment evaluates. The
unsafe renderer evaluates '{{ ().__class__.__bases__ }}'; the sandboxed renderer raises."""

from harnesses.lib import jinja_ssti_sandbox_test_harness as h


def test_proof_unsafe_renderer_executes_escape() -> None:
    assert h.executes_escape(h.UnsafeRenderer) is True


def test_proof_sandboxed_renderer_blocks_escape() -> None:
    assert h.executes_escape(h.SandboxedRenderer) is False


def test_proof_sandboxed_renderer_renders_benign() -> None:
    assert h.renders_benign(h.SandboxedRenderer) is True


# --- scenario coverage: a plain Environment evaluates the attribute traversal ---
def test_proof_unsafe_renderer_evaluates_attribute() -> None:
    out = h.UnsafeRenderer().render("{{ ''.__class__ }}")
    assert "class" in out


# --- third pass (researched): a plain Environment reaches the __subclasses__ RCE primitive ---
def test_proof_unsafe_renderer_reaches_subclasses_chain() -> None:
    out = h.UnsafeRenderer().render("{{ ''.__class__.__mro__[1].__subclasses__() }}")
    assert "class" in out


import pytest  # noqa: E402


@pytest.mark.parametrize("payload", [
    "{{ namespace.__init__.__globals__ }}",
    "{{ ''.__class__.__mro__[1].__subclasses__() }}",
])
def test_proof_plain_env_reaches_gadget(payload) -> None:
    out = h.UnsafeRenderer().render(payload)
    assert len(out) > 50 and ("{" in out or "[" in out), payload
