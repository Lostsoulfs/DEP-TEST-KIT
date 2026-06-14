#!/bin/bash
# PostToolUse hook: auto-format/lint-fix a Python file right after the agent edits
# it, so style is enforced mechanically. Safe fixes only (ruff's default --fix
# class; never --unsafe-fixes), mirroring the report-only logic invariant (ADR-0003).
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
[ -z "${file:-}" ] && exit 0
[ -f "$file" ] || exit 0

case "$file" in
  *.py)
    uv run ruff format "$file" >/dev/null 2>&1 || true
    uv run ruff check --fix "$file" >/dev/null 2>&1 || true
    ;;
esac
exit 0
