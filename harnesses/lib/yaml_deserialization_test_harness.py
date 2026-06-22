#!/usr/bin/env python3
"""Unsafe YAML deserialization harness (PyYAML).

OWASP Top 10:2025 A08 Software & Data Integrity Failures (insecure deserialization). Still a
live 2026 class -- e.g. JumpServer renders attacker-uploaded YAML, and `yaml.load` with the
full loader will instantiate arbitrary Python objects from `!!python/...` tags.

WHY: A test that loads `{a: 1, b: 2}` passes for BOTH `yaml.safe_load` and the full
`yaml.load`. The integrity failure only shows on a tag-bearing document: the full loader
constructs a Python object from untrusted input (the mechanism behind arbitrary code
execution), while `safe_load` refuses the tag. A mock models neither.

HOW: `SafeYamlLoader` is the ORACLE -- `yaml.safe_load`, which raises on `!!python/...` tags.
`UnsafeYamlLoader` is the planted defect -- `yaml.load(text, Loader=yaml.Loader)`.
`constructs_python_object` feeds a (harmless) object-construction tag: the unsafe loader
constructs it (proving arbitrary callables fire), the safe loader refuses.

WHERE: lib/ -- in-process, deterministic. Adds `pyyaml` to the matching extra.

Self-test:
    python harnesses/lib/yaml_deserialization_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys

import yaml

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["constructs_python_object"]

DOSSIER = {
    "name": "yaml_deserialization",
    "path": "harnesses/lib/yaml_deserialization_test_harness.py",
    "flavor": "lib",
    "dependency": "pyyaml",
    "standard": "OWASP Top 10:2025 A08 Integrity Failures (insecure deserialization)",
    "failure_class": (
        "Untrusted YAML loaded with the full loader -> arbitrary Python object construction"
    ),
    "oracle": "SafeYamlLoader.load — yaml.safe_load (refuses !!python/... tags)",
    "buggy": "UnsafeYamlLoader.load — yaml.load(Loader=yaml.Loader)",
    "planted_mutant": (
        "a '!!python/object/apply:builtins.tuple' tag; full loader constructs it, safe refuses"
    ),
    "proof_file": "tests/lib/test_yaml_deserialization_proof.py",
    "vacuity_targets": ["constructs_python_object"],
    "commands": ["python harnesses/lib/yaml_deserialization_test_harness.py --self-test"],
    "known_limits": (
        "uses a harmless construction tag; the same path enables os.system-style payloads"
    ),
    "related": ["appsec DeserializationChecker", "ast_sast PY-YAML-LOAD"],
}

# A harmless object-construction tag: it builds a tuple rather than running a command, but it
# proves the full loader will invoke arbitrary callables from untrusted YAML (the vuln class).
_OBJECT_TAG = "!!python/object/apply:builtins.tuple [[1, 2, 3]]"


class SafeYamlLoader:
    """ORACLE: refuse Python-object tags."""

    def load(self, text: str):
        return yaml.safe_load(text)


class UnsafeYamlLoader:
    """BUGGY: the full loader constructs Python objects from tags."""

    def load(self, text: str):
        return yaml.load(text, Loader=yaml.Loader)  # noqa: S506 -- the intentional defect


def loads_plain_mapping(make_loader) -> bool:
    try:
        return make_loader().load("a: 1\nb: 2") == {"a": 1, "b": 2}
    except Exception:
        return False


def constructs_python_object(make_loader) -> bool:
    """True == the loader constructed a Python object from the tag (unsafe); False == refused."""
    try:
        result = make_loader().load(_OBJECT_TAG)
        return result == (1, 2, 3)   # the tag fired and built a tuple -> arbitrary construction
    except Exception:
        return False                 # safe_load refused the tag


def run_self_test() -> int:
    failures = 0
    if not loads_plain_mapping(SafeYamlLoader):
        failures += 1
        print("FAIL: oracle could not load a plain mapping", file=sys.stderr)
    if constructs_python_object(SafeYamlLoader):
        failures += 1
        print("FAIL: oracle constructed a Python object from a tag", file=sys.stderr)
    if not constructs_python_object(UnsafeYamlLoader):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: full loader was NOT caught constructing a Python object", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (safe_load refuses the tag; full loader caught constructing an object)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unsafe YAML deserialization harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
