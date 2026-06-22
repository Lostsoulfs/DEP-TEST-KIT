"""Oracle + CLI-contract test for xxe_defense (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_xxe_defense_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import xxe_defense_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.parses_plain_xml(h.SafeXmlParser) is True


import pytest  # noqa: E402

_XXE_DOCS = [
    '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "EXPANDED-SECRET">]><r>&x;</r>',
    '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "AA">]><r>&a;</r>',
    '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "x"><!ENTITY b "&a;&a;">]><r>&b;</r>',
    '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY g "&#65;&#66;">]><r>&g;</r>',
]


@pytest.mark.parametrize("xml", _XXE_DOCS)
def test_oracle_refuses_entity_definition(xml) -> None:
    try:
        h.SafeXmlParser().parse(xml)
        refused = False
    except Exception:
        refused = True
    assert refused is True, xml


_PLAIN_XML = [
    ("<r>hello</r>", "hello"), ("<r>123</r>", "123"),
    ("<r>a b c</r>", "a b c"), ("<doc>text</doc>", "text"),
]


@pytest.mark.parametrize("xml,expected", _PLAIN_XML)
def test_oracle_parses_plain_xml(xml, expected) -> None:
    assert h.SafeXmlParser().parse(xml) == expected, xml


# === our own / batch 5 (original; math coverage) ===
# Knox (absurd/sw): the classic file-read XXE uses an EXTERNAL (SYSTEM) entity and the stealthy
# variant a PARAMETER entity -- defusedxml refuses both (EntitiesForbidden). An external-DTD
# reference with no entities parses safely (defusedxml does not fetch it).
def test_oracle_refuses_external_and_parameter_entities() -> None:
    ext = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>'
    param = '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY % p SYSTEM "http://e/e">%p;]><r>ok</r>'
    for xml in (ext, param):
        try:
            h.SafeXmlParser().parse(xml)
            refused = False
        except Exception:
            refused = True
        assert refused is True, xml
    dtd = '<?xml version="1.0"?><!DOCTYPE r SYSTEM "http://evil.example/x.dtd"><r>ok</r>'
    assert h.SafeXmlParser().parse(dtd) == "ok"  # external DTD not fetched -> safe parse
