#!/bin/bash
# PreToolUse hook: block edits to generated/derived files and secret/credential
# files that must never be hand-edited. Exit 2 denies the tool call with the message.
set -euo pipefail

input=$(cat)
file=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
[ -z "${file:-}" ] && exit 0

case "$file" in
  */uv.lock | uv.lock)
    echo "Refusing to hand-edit uv.lock — it's generated. Use uv (uv lock / uv sync)." >&2
    exit 2
    ;;
  */sbom.cdx.json | sbom.cdx.json | *.sbom.json)
    echo "Refusing to hand-edit a generated SBOM — regenerate via 'make sbom'." >&2
    exit 2
    ;;
  */.venv/* | .venv/* | */dist/* | dist/* | */build/* | build/*)
    echo "Refusing to edit build output / virtualenv (.venv, dist, build)." >&2
    exit 2
    ;;
  *.pem | *.key | *.p12 | *.keystore | .env | */.env | .env.* | */.env.*)
    echo "Refusing to write secret/credential files (.env, *.key, *.pem, ...)." >&2
    exit 2
    ;;
esac
exit 0
