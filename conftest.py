"""Pytest configuration shared across the suite.

The `lib` lane runs everywhere (pure in-process). The `integration` lane needs a
Docker daemon; when none is present those tests are skipped with a clear reason
rather than failing, so a laptop without Docker still gets a green `lib` run and
CI's dedicated Docker job runs the full set.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest


def _docker_available() -> bool:
    # The binary alone isn't enough — a daemon must answer, or testcontainers errors
    # out instead of the tests being skipped. `docker info` returns 0 only when the
    # daemon is reachable (true in CI's integration job, false on a daemonless box).
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _docker_available():
        return
    skip_integration = pytest.mark.skip(
        reason="Docker not available; integration harness needs a daemon"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
