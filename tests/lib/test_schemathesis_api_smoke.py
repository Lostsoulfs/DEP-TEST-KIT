"""Smoke test: pin the deeper-than-public schemathesis API the openapi_fuzz harness uses.

`openapi_fuzz_test_harness.py` imports `schemathesis.core.failures.FailureGroup` and calls
`schemathesis.openapi.from_wsgi(...)` — internal-ish paths with no stability guarantee. A
schemathesis upgrade that moves or renames them should fail HERE with a clear message, not as a
confusing error inside the harness. If a Renovate bump trips this, update the harness import and
this test in lockstep. (MoE E6 lens: "fragile internal imports guarded by a version smoke test".)
"""

import importlib


def test_failuregroup_import_path() -> None:
    mod = importlib.import_module("schemathesis.core.failures")
    assert hasattr(mod, "FailureGroup"), \
        "schemathesis.core.failures.FailureGroup moved/renamed — update openapi_fuzz harness"


def test_openapi_from_wsgi_available() -> None:
    import schemathesis

    assert hasattr(schemathesis, "openapi"), "schemathesis.openapi namespace moved"
    assert hasattr(schemathesis.openapi, "from_wsgi"), \
        "schemathesis.openapi.from_wsgi moved/renamed — update openapi_fuzz harness"
