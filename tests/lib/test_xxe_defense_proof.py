"""Proof: defusedxml refuses the entity the stdlib parser expands.
&x; raises EntitiesForbidden vs expanding to the injected value."""

from harnesses.lib import xxe_defense_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.expands_entity(h.UnsafeXmlParser) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.expands_entity(h.SafeXmlParser) is False


def test_proof_oracle_happy_path() -> None:
    assert h.parses_plain_xml(h.SafeXmlParser) is True


import pytest  # noqa: E402

_XXE_EXPANSIONS = [
    ('<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "EXPANDED-SECRET">]><r>&x;</r>',
     "EXPANDED-SECRET"),
    ('<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "AA">]><r>&a;</r>', "AA"),
    ('<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "x"><!ENTITY b "&a;&a;">]><r>&b;</r>', "xx"),
    ('<?xml version="1.0"?><!DOCTYPE r [<!ENTITY g "&#65;&#66;">]><r>&g;</r>', "AB"),
]


@pytest.mark.parametrize("xml,expected", _XXE_EXPANSIONS)
def test_proof_unsafe_parser_expands_entity(xml, expected) -> None:
    assert h.UnsafeXmlParser().parse(xml) == expected, xml
