---
description: The mandatory pre-push gate (ADR-0002/0003) — every gate strict, plus the MoE panel and the semantic self-review. Run before EVERY push; zero failures and zero high-severity findings required.
allowed-tools: Bash(make:*), Bash(uv run:*), Bash(git fetch:*), Bash(git diff:*), Bash(git log:*), Read, Grep, Glob
---

Run the full pre-push gate:

1. `git fetch origin main --quiet` (so the audit range is honest).
2. `make all` — sync(--locked) → ruff → deptry → lib lane → per-harness self-tests →
   uv audit. Any non-zero exit = NOT pushable. If Docker is present, also `make test-int`.
3. `uv run python tools/audit_drift.py --base origin/main --head HEAD --run-checks --strict`.
   A high-severity finding (exit 1) = NOT pushable.
4. **MoE panel** (`docs/moe-audit.md`): route the change, run each lens, require a
   verdict with evidence. Blocking lenses (E3 Teeth, E5 Supply-chain) must pass.
5. **Semantic self-review**: read the full diff vs. the claims in the commits/PR body.
   Hunt for what the green checks DON'T prove — phantom claims, scope creep, weakened
   gates, a harness without a real planted-bug proof. For large diffs, spawn the
   auditor subagent.
6. If the environment can't run a gate (e.g. `uv audit` unavailable in an older uv),
   record it verbatim as SKIPPED(env) in the PR body and verify via CI. Never report a
   skipped gate as green.
7. Paste the gate + audit summary and the lens verdicts into the PR's `## Self-audit`
   section; fill `## Deviations from plan` honestly.

Only when 1–7 are clean: push. Self-initiated, every push, no exceptions.
