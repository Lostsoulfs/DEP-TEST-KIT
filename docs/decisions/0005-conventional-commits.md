# 0005 — Conventional Commits enforced by gitlint

Status: accepted (2026-06-14). Records that commit titles follow Conventional Commits,
enforced locally (pre-commit `commit-msg`) and in CI (an advisory PR range check).

## Context
The verify+gap pass on two 2026 CI research docs
(`docs/CI_RESEARCH_VERIFICATION_2026-06-14.md`) confirmed against primary sources that
gitlint's `contrib-title-conventional-commits` rule (CT1), binding it to the pre-commit
`commit-msg` stage with `--msg-filename`, and a CI `gitlint --commits BASE..HEAD` range
check are the standard, low-maintenance way to enforce Conventional Commits on a small
Python repo — and that this unlocks future `semantic-release`. The repo already uses
conventional-style titles informally; this makes it a checked invariant. (The Gemini
doc's gitlint claims verified; its hype statistics did not — see the verification doc.)

## Decision
- `gitlint` stays a **standalone CLI**, not a project dependency: its `sh` dependency
  (Unix `fcntl`) cannot build on Windows under `uv sync`, and the project never imports
  it (same status as the `mutmut` runner). Local: `uv tool install gitlint-core`; CI:
  `uvx --from gitlint-core gitlint`. Keeps `uv.lock` clean and Windows-buildable.
- `.gitlint`: activate `contrib=contrib-title-conventional-commits`; `title-max-length=72`;
  `ignore=body-is-missing` (allow one-line commits); ignore merge/fixup/squash/revert;
  `body-max-line-length=120`.
- Local: a pre-commit `commit-msg` hook (`gitlint --staged --msg-filename`), installed via
  `uvx pre-commit install --install-hooks` (the config sets `default_install_hook_types`).
- CI: a `Commit Lint` workflow runs `gitlint --commits origin/<base>..HEAD` on PRs.
  **Advisory** — not yet a required check (see `SETTINGS-CHECKLIST.md`); promote to
  required once comfortable.

## Consequence
- Commit history stays machine-parseable, enabling `semantic-release` later.
- The gate is title-focused and lightweight; bodies are loosely bounded (120 cols).
- Local enforcement needs `pre-commit install --install-hooks` once (documented in-config).
- Does not block merges until made a required check — fail-open by design for now.
