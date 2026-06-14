"""Pytest configuration shared across the suite.

The `lib` lane runs everywhere (pure in-process). The `integration` lane needs a
Docker daemon; when none is present those tests are skipped with a clear reason
rather than failing, so a laptop without Docker still gets a green `lib` run and
CI's dedicated Docker job runs the full set.
"""

from __future__ import annotations

import shutil

import pytest


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _docker_available():
        return
    skip_integration = pytest.mark.skip(
        reason="Docker not available; integration harness needs a daemon"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
