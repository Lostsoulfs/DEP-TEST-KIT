"""Oracle + CLI-contract test for jinja_ssti_sandbox (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_jinja_ssti_sandbox_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import jinja_ssti_sandbox_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.renders_benign(h.SandboxedRenderer) is True


# --- scenario coverage: the sandbox refuses every attribute-traversal SSTI probe ---
_SSTI = [
    "{{ ''.__class__.__mro__ }}",
    "{{ ().__class__.__bases__ }}",
    "{{ [].__class__.__mro__ }}",
]


def test_oracle_renders_benign_template() -> None:
    assert h.SandboxedRenderer().render("Hello {{ name }}", name="Alice") == "Hello Alice"


def test_oracle_refuses_every_ssti_probe() -> None:
    renderer = h.SandboxedRenderer()
    for probe in _SSTI:
        try:
            renderer.render(probe)
            rendered = True
        except Exception:
            rendered = False
        assert rendered is False, probe


# --- second pass: richer benign templates; more SSTI probes refused ---
def test_oracle_renders_more_benign_templates() -> None:
    renderer = h.SandboxedRenderer()
    assert renderer.render("{{ a + b }}", a=2, b=3) == "5"
    assert renderer.render("{{ name|upper }}", name="bob") == "BOB"


def test_oracle_refuses_more_ssti_probes() -> None:
    renderer = h.SandboxedRenderer()
    probes = [
        "{{ cycler.__init__.__globals__ }}",
        "{{ ''.__class__.mro() }}",
        "{{ ''.__class__.__base__.__subclasses__() }}",
    ]
    for probe in probes:
        try:
            renderer.render(probe)
            rendered = True
        except Exception:
            rendered = False
        assert rendered is False, probe


# --- third pass: garbage / undefined templates never leak internals ---
def test_oracle_garbage_templates_never_leak_internals() -> None:
    renderer = h.SandboxedRenderer()
    for tmpl in ["{{ config }}", "{{ self }}", "{{ undefined_var }}"]:
        try:
            out = renderer.render(tmpl)
        except Exception:
            out = ""
        assert "class '" not in out and "function" not in out, tmpl


# --- third pass (researched): documented 2026 Jinja2 RCE chains must be refused ---
# Sources: PayloadsAllTheThings (Python SSTI); SGLang CVE-2026-5760; NetBox CVE-2026-29514.
def test_oracle_refuses_documented_rce_chains() -> None:
    renderer = h.SandboxedRenderer()
    payloads = [
        "{{ cycler.__init__.__globals__ }}",
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
        "{{ namespace.__init__.__globals__ }}",
        "{{ self.__init__.__globals__ }}",
        "{{ ''.__class__.__base__.__subclasses__() }}",
    ]
    for payload in payloads:
        try:
            renderer.render(payload)
            reached = True
        except Exception:
            reached = False
        assert reached is False, payload


import pytest  # noqa: E402

# --- pass 4 (researched corpus, PayloadsAllTheThings): distinct SSTI techniques ---
# Verified live: SandboxedEnvironment refuses RCE-reachable gadget/traversal techniques
# and neutralizes attr-filter / subscript / func-globals evasions.
_SSTI_REFUSED = [
    "{{ joiner.__init__.__globals__ }}",
    "{{ ().__class__.__bases__[0].__subclasses__() }}",
    "{{ ''.__class__.mro()[1].__subclasses__() }}",
    "{{ ''.__getattribute__('__class__') }}",
    "{{ ''.__class__.__dict__ }}",
    "{{ ''.__class__.__init__.__globals__ }}",
    "{{ ''.__class__.__subclasses__() }}",
    "{{ ''.__class__.__base__ }}",
]


@pytest.mark.parametrize("payload", _SSTI_REFUSED)
def test_oracle_refuses_ssti_technique(payload) -> None:
    try:
        h.SandboxedRenderer().render(payload)
        reached = True
    except Exception:
        reached = False
    assert reached is False, payload


_SSTI_NEUTRALIZED = [
    "{{ ''['__class__'] }}",
    "{{ ''|attr('__class__') }}",
    "{{ ''.format.__globals__ }}",
    "{{ lipsum.__globals__ }}",
]


@pytest.mark.parametrize("payload", _SSTI_NEUTRALIZED)
def test_oracle_neutralizes_ssti_evasion(payload) -> None:
    try:
        out = h.SandboxedRenderer().render(payload)
    except Exception:
        out = ""
    assert "class '" not in out and "globals" not in out and "function" not in out, payload


@pytest.mark.parametrize("payload", [
    "{{ ''.__class__.__base__.__base__ }}",
    "{{ ''.__class__.__qualname__ }}",
    "{{ ''.__class__.__flags__ }}",
    "{{ ''.__class__.__name__ }}",
    "{{ [].__class__.__base__.__subclasses__() }}",
])
def test_oracle_refuses_more_class_introspection(payload) -> None:
    try:
        h.SandboxedRenderer().render(payload)
        reached = True
    except Exception:
        reached = False
    assert reached is False, payload
