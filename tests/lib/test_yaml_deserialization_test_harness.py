"""Oracle + CLI-contract test for yaml_deserialization (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_yaml_deserialization_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import yaml_deserialization_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.loads_plain_mapping(h.SafeYamlLoader) is True


# --- scenario coverage: safe_load refuses every python-object tag (none are executable here) ---
_PY_TAGS = [
    "!!python/object/apply:builtins.tuple\n- [1, 2, 3]",
    "!!python/name:builtins.print",
    "!!python/object/new:builtins.Exception\nargs: ['x']",
]


def test_oracle_loads_plain_mapping() -> None:
    assert h.SafeYamlLoader().load("a: 1\nb: 2") == {"a": 1, "b": 2}


def test_oracle_refuses_every_python_tag() -> None:
    loader = h.SafeYamlLoader()
    for tag in _PY_TAGS:
        try:
            loader.load(tag)
            constructed = True
        except Exception:
            constructed = False
        assert constructed is False, tag


# --- second pass: richer benign YAML; more python tags refused ---
def test_oracle_loads_more_benign_yaml() -> None:
    loader = h.SafeYamlLoader()
    assert loader.load("items:\n- 1\n- 2\n- 3") == {"items": [1, 2, 3]}
    assert loader.load("nested:\n  a: 1\n  b: 2") == {"nested": {"a": 1, "b": 2}}


def test_oracle_refuses_more_python_tags() -> None:
    loader = h.SafeYamlLoader()
    tags = [
        "!!python/object/apply:builtins.dict\n- {}",
        "!!python/module:os",
        "!!python/object/new:builtins.list\n- [1, 2]",
    ]
    for tag in tags:
        try:
            loader.load(tag)
            constructed = True
        except Exception:
            constructed = False
        assert constructed is False, tag


# --- third pass: safe_load only ever yields plain builtin types ---
def test_oracle_only_returns_builtin_types() -> None:
    loader = h.SafeYamlLoader()
    for text in ["a: 1", "[1, 2, 3]", "key: [a, b]", "n: null", "f: 1.5"]:
        result = loader.load(text)
        assert result is None or isinstance(result, (dict, list, str, int, float, bool)), text


import pytest  # noqa: E402

# --- pass 4 (researched corpus): PyYAML python-tag gadget forms ---
# safe_load must refuse every python/* tag (apply/new/name/module/object/tuple).
_YAML_TAGS = [
    "!!python/object/apply:builtins.tuple\n- [1, 2, 3]",
    "!!python/object/apply:builtins.list\n- [1, 2]",
    "!!python/object/apply:builtins.dict\n- [[a, 1]]",
    "!!python/object/apply:builtins.set\n- [[1, 2]]",
    "!!python/object/new:builtins.Exception\nargs: ['x']",
    "!!python/object/new:builtins.list",
    "!!python/name:builtins.print",
    "!!python/name:os.system",
    "!!python/module:os",
    "!!python/object:http.cookies.SimpleCookie {}",
    "!!python/tuple [1, 2]",
]


@pytest.mark.parametrize("payload", _YAML_TAGS)
def test_oracle_refuses_python_tag_form(payload) -> None:
    try:
        h.SafeYamlLoader().load(payload)
        constructed = True
    except Exception:
        constructed = False
    assert constructed is False, payload


# === our own / batch 5 (original; KNOWN LIMIT, web-checked) ===
# Adeyemi (whimsical/psych) -- safe_load blocks Python-object construction (RCE) but still
# EXPANDS YAML anchors/aliases; deeply-nested aliases are the "billion laughs" DoS
# (CVE-2019-11253, the Kubernetes YAML bomb). Honest gap: safe_load stops exec, not the DoS.
def test_oracle_known_limit_aliases_expand_yaml_bomb() -> None:
    loaded = h.SafeYamlLoader().load("base: &a [1, 2]\nx: *a\ny: *a")
    assert loaded["x"] == [1, 2] and loaded["y"] == [1, 2]  # aliases expanded (small, bounded)
    try:
        h.SafeYamlLoader().load(h._OBJECT_TAG)  # the object tag is still refused
        refused = False
    except Exception:
        refused = True
    assert refused is True
