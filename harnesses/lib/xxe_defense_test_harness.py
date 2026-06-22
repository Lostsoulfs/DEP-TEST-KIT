#!/usr/bin/env python3
"""XXE harness (defusedxml): refuse XML entity expansion / external entities.

OWASP Top 10:2025 A05 Injection (XML External Entity, CWE-611).

WHY: An XML parser that processes a `<!DOCTYPE ... <!ENTITY ...>>` lets an attacker expand
entities -- exfiltrating files via external entities or blowing up memory (billion laughs). A
hardened parser refuses entity definitions outright.

HOW: `SafeXmlParser` is the ORACLE -- `defusedxml.ElementTree`, which raises
`EntitiesForbidden` on any entity. `UnsafeXmlParser` is the planted defect -- stdlib
`xml.etree.ElementTree`, which expands the internal entity. `expands_entity` parses a document
whose body is an entity reference and reports whether it expanded to the injected value.

WHERE: lib/ -- dependency-backed (`defusedxml`), in-process.

Self-test:
    python harnesses/lib/xxe_defense_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from typing import Callable

import defusedxml.ElementTree as DET

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["expands_entity"]

DOSSIER = {
    "name": "xxe_defense",
    "path": "harnesses/lib/xxe_defense_test_harness.py",
    "flavor": "lib",
    "dependency": "defusedxml",
    "standard": "OWASP Top 10:2025 A05 Injection - XML External Entity (CWE-611)",
    "failure_class": "An XML parser that expands DTD entities (file exfiltration / billion laughs)",
    "oracle": "SafeXmlParser.parse - defusedxml refuses entity definitions (EntitiesForbidden)",
    "buggy": "UnsafeXmlParser.parse - stdlib ElementTree expands the internal entity",
    "planted_mutant": "a document whose body &x; expands to an injected value",
    "proof_file": "tests/lib/test_xxe_defense_proof.py",
    "vacuity_targets": ["expands_entity"],
    "commands": ["python harnesses/lib/xxe_defense_test_harness.py --self-test"],
    "known_limits": "entity-expansion refusal; not full schema validation or XInclude review",
    "related": ["yaml_deserialization", "advanced_injection"],
}

_XXE = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "EXPANDED-SECRET">]><r>&x;</r>'


class SafeXmlParser:
    """ORACLE: defusedxml refuses entity definitions."""

    def parse(self, xml: str):
        return DET.fromstring(xml).text


class UnsafeXmlParser:
    """BUGGY: stdlib ElementTree expands the internal entity."""

    def parse(self, xml: str):
        return ET.fromstring(xml).text


def parses_plain_xml(make_parser: Callable[[], object]) -> bool:
    return make_parser().parse("<r>hello</r>") == "hello"


def expands_entity(make_parser: Callable[[], object]) -> bool:
    """True == the injected entity expanded into the parsed value (XXE)."""
    try:
        return make_parser().parse(_XXE) == "EXPANDED-SECRET"
    except Exception:
        return False


def run_self_test() -> int:
    failures = 0
    if not parses_plain_xml(SafeXmlParser):
        failures += 1
        print("FAIL: oracle failed to parse plain XML", file=sys.stderr)
    if expands_entity(SafeXmlParser):
        failures += 1
        print("FAIL: oracle expanded an XML entity", file=sys.stderr)
    if not expands_entity(UnsafeXmlParser):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: unsafe parser entity expansion was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (defusedxml refuses the entity; stdlib parser expands it -- caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="XXE defense harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
