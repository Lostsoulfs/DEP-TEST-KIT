# 0003 — Agent scaffolding and self-audit enforcement (mirrors Codex)

Status: accepted (2026-06-14). Records the upgrade that brings DEP-TEST-KIT's agent
scaffolding and self-audit to parity with `Codex-Speed-Test`, the platform where these
patterns matured. This repo was created before that upgrade path existed.

## Context
ADR-0002 defined the self-audit *policy* and the MoE audit panel as documentation only,
with enforcement deferred for explicit sign-off. The operator authorized mirroring
Codex "in every way related." Codex's mechanism is: a committed `.claude/` (settings +
hooks + role agents + commands), a deterministic drift auditor invoked in a self-
initiated pre-push preflight (its ADR-0007), and a `docs/LEARNINGS.md` log. DEP-TEST-KIT
had the gates but none of this scaffolding.

## Decision

### Mirror Codex's `.claude/`, adapted npm/biome → uv/ruff/pytest
- `settings.json`: SessionStart (`uv sync`), PreToolUse `guard.sh` (block hand-edits to
  `uv.lock`, SBOMs, `.venv`/build, secrets), PostToolUse `format.sh` (`ruff format` +
  safe `ruff check --fix`) and `log.sh` (JSONL event log, gitignored). A permissions
  allowlist for the routine uv/ruff/pytest/git commands.
- `agents/`: `auditor` (read-only; runs the drift auditor + MoE panel + semantic
  review; report-only on logic; safe auto-fix only), `explorer`, `planner`.
- `commands/`: `preflight`, `audit`, `ship`, `adr`, `end-session`, `audit-retro`.

### Deterministic drift auditor: `tools/audit_drift.py`
A stdlib-only port of Codex's `scripts/audit-drift.mjs`. Same shape (refuse empty
range; scan added lines for suppressions / skipped tests / TODO / debug; sensitive-path
and deviation checks; `--run-checks`, `--fix` safe-only, `--strict`, `--history`).
Repo-specific addition: the **harness-completeness invariant** — every harness must
ship a paired test AND a planted-bug proof, the structural form of the anti-vacuous-
green rule (ADR-0001).

### Self-audit is enforced, not just documented
The pre-push preflight runs `make all` + the drift auditor `--strict` + the MoE panel +
a semantic review. Logic-affecting fixes are report-only; the auto-fix class is
`ruff format` + `ruff check --fix` (never `--unsafe-fixes`) and never widens.

### Invariant: the auditor never drifts the code to pass
Mirrors Codex ADR-0007. The audit may format, never alter logic, skip tests, or weaken
a gate to make itself green. `/audit-retro` stays manual and propose-only.

## Consequence
Any agent working in this repo inherits the same self-audit path: hooks enforce
formatting and block generated/secret edits mechanically, the auditor agent runs the
deterministic + semantic + MoE review before every push, and outcomes are logged to
`docs/LEARNINGS.md`. The CI-side `audit.yml` workflow runs the auditor on every PR,
posts the report as a comment (report-only, so PR heads stay mergeable), and uploads the
run's history line as a CI artifact for `/audit-retro` — it never pushes (see ADR-0004
for why the two pushing variants were abandoned). On its first run the auditor caught
real drift (unnecessary suppressions in Batch 1) — evidence the gate has teeth.
