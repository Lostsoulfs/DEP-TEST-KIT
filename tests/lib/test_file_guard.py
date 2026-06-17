"""Tests for tools/file_guard.py — and proof the guard actually bites.

(a) the committed .fileguard.json must match the live gate machinery (so a gate file
that changed without a re-baseline fails CI — the whole point); (b) against a throwaway
tree, the guard must report clean, then BITE on a modified file, a removed file, an
unbaselined add, a missing / corrupt / schema-invalid baseline, and refuse a snapshot
it cannot write — every failure NAMED, never a bare crash.
"""

from __future__ import annotations

from pathlib import Path

from tools import file_guard

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_working_tree_matches_committed_baseline() -> None:
    # If a protected gate file changed without re-baselining, this fails loudly.
    assert file_guard.check(REPO_ROOT, REPO_ROOT / file_guard.MANIFEST_NAME) == 0


def _stage(tmp: Path) -> None:
    (tmp / "a.txt").write_text("alpha\n", encoding="utf-8")
    (tmp / "sub").mkdir()
    (tmp / "sub" / "b.txt").write_text("beta\n", encoding="utf-8")


def test_clean_modified_removed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(file_guard, "PROTECTED_FILES", ["a.txt", "sub/b.txt"])
    _stage(tmp_path)
    m = tmp_path / ".fileguard.json"
    assert file_guard.update(tmp_path, m) == 0
    assert file_guard.check(tmp_path, m) == 0  # clean
    (tmp_path / "a.txt").write_text("alpha CHANGED\n", encoding="utf-8")
    assert file_guard.check(tmp_path, m) == 1  # MODIFIED bites
    (tmp_path / "a.txt").write_text("alpha\n", encoding="utf-8")
    assert file_guard.check(tmp_path, m) == 0  # restored
    (tmp_path / "sub" / "b.txt").unlink()
    assert file_guard.check(tmp_path, m) == 1  # REMOVED bites


def test_unbaselined_add(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(file_guard, "PROTECTED_FILES", ["a.txt", "sub/b.txt"])
    _stage(tmp_path)
    m = tmp_path / ".fileguard.json"
    assert file_guard.update(tmp_path, m) == 0
    monkeypatch.setattr(file_guard, "PROTECTED_FILES", ["a.txt", "sub/b.txt", "c.txt"])
    (tmp_path / "c.txt").write_text("gamma\n", encoding="utf-8")
    assert file_guard.check(tmp_path, m) == 1  # UNBASELINED bites


def test_missing_corrupt_and_schema_invalid_baselines(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(file_guard, "PROTECTED_FILES", ["a.txt", "sub/b.txt"])
    _stage(tmp_path)
    m = tmp_path / ".fileguard.json"
    assert file_guard.check(tmp_path, m) == 2  # missing
    for bad in ("{ not valid json", "[]", '{"files": null}', '{"files": {"a.txt": 123}}'):
        m.write_text(bad, encoding="utf-8")
        assert file_guard.check(tmp_path, m) == 2, bad  # corrupt / schema-invalid


def test_update_refuses_unwritable_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(file_guard, "PROTECTED_FILES", ["a.txt", "sub/b.txt"])
    _stage(tmp_path)
    # Parent dir does not exist -> write_text raises OSError -> NAMED refusal, not a crash.
    assert file_guard.update(tmp_path, tmp_path / "nope" / "x.json") == 1
