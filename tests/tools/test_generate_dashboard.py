from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def write_status(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-19T12:00:00Z",
                "claim_scope": (
                    "current proof baseline; fixture-defined proof under current tooling; "
                    "does not claim total correctness or production assurance"
                ),
                "counts": {
                    "harnesses": 1,
                    "lib": 1,
                    "integration": 0,
                    "ai": 0,
                    "teeth_verified": 1,
                    "teeth_eligible": 1,
                    "exceptions": 0,
                },
                "source": {"mode": "test fixture"},
                "harnesses": [
                    {
                        "id": "lib/<script>alert(1)</script>",
                        "flavor": "lib",
                        "status": "proof source present",
                        "proof_type": "fixture-defined proof",
                        "teeth_state": "verified",
                        "summary": "Escaping fixture <b>must stay text</b>.",
                        "source_files": ["harnesses/lib/example.py"],
                        "commands": ["uv run --frozen pytest tests/lib/test_example.py -q"],
                        "next_test_path": "Keep dynamic text escaped.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def run_dashboard(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/generate_dashboard.py", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_dashboard_escapes_dynamic_html(tmp_path: Path) -> None:
    status = tmp_path / "STATUS.json"
    output = tmp_path / "index.html"
    write_status(status)

    result = run_dashboard("--status", str(status), "--output", str(output))

    assert result.returncode == 0, result.stderr
    html = output.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>must stay text</b>" not in html
    assert "does not claim total correctness" in html


def test_dashboard_check_fails_when_committed_output_is_stale(tmp_path: Path) -> None:
    status = tmp_path / "STATUS.json"
    output = tmp_path / "index.html"
    write_status(status)
    output.write_text("stale", encoding="utf-8")

    result = run_dashboard("--status", str(status), "--output", str(output), "--check")

    assert result.returncode == 1
    assert "stale dashboard" in result.stderr


def test_dashboard_check_passes_without_committed_output(tmp_path: Path) -> None:
    status = tmp_path / "STATUS.json"
    output = tmp_path / "index.html"
    write_status(status)

    result = run_dashboard("--status", str(status), "--output", str(output), "--check")

    assert result.returncode == 0, result.stderr
    assert not output.exists()
