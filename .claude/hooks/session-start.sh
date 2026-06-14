#!/bin/bash
set -euo pipefail

# SessionStart hook for Claude Code on the web.
# Provisions the locked environment so the lib/integration lanes, ruff, deptry,
# and the per-harness self-tests work out of the box in a fresh remote container.

# Only run in remote (web) sessions; local machines already have their setup.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Locked, reproducible env with all harness extras. `uv sync` is idempotent, so a
# cached container self-heals; --all-extras pulls both lib and integration deps.
uv sync --all-extras || {
  echo "uv sync failed at session start — run 'make sync' once network is available." >&2
}
exit 0
