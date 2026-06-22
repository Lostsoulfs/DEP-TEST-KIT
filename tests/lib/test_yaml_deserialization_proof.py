"""Proof: safe_load refuses the object-construction tag the full loader fires. The unsafe
loader constructs a Python object from '!!python/object/apply'; safe_load refuses it."""

from harnesses.lib import yaml_deserialization_test_harness as h


def test_proof_unsafe_loader_constructs_object() -> None:
    assert h.constructs_python_object(h.UnsafeYamlLoader) is True


def test_proof_safe_loader_refuses_object() -> None:
    assert h.constructs_python_object(h.SafeYamlLoader) is False


def test_proof_safe_loader_loads_plain_mapping() -> None:
    assert h.loads_plain_mapping(h.SafeYamlLoader) is True


# --- scenario coverage: the full loader constructs a Python object from a tag ---
def test_proof_unsafe_loader_constructs_tuple() -> None:
    result = h.UnsafeYamlLoader().load("!!python/object/apply:builtins.tuple\n- [1, 2, 3]")
    assert result == (1, 2, 3)


import pytest  # noqa: E402

# --- pass 4 (researched): the full loader constructs an object from each inert tag ---
_YAML_CONSTRUCTS = [
    "!!python/object/apply:builtins.tuple\n- [1, 2, 3]",
    "!!python/object/apply:builtins.list\n- [1, 2]",
    "!!python/object/apply:builtins.dict\n- [[a, 1]]",
    "!!python/object/new:builtins.Exception\nargs: ['x']",
    "!!python/name:builtins.print",
    "!!python/object:http.cookies.SimpleCookie {}",
    "!!python/tuple [1, 2]",
]


@pytest.mark.parametrize("payload", _YAML_CONSTRUCTS)
def test_proof_full_loader_constructs_object(payload) -> None:
    result = h.UnsafeYamlLoader().load(payload)
    assert result is not None, payload
