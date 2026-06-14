# CLAUDE.md - DEP-TEST-KIT

The filename is historical. This is a universal instruction source for every human,
agent, and automation system in this repository. Read it together with `AGENTS.md`
and `SECURITY.md`; all rules there apply regardless of the tool in use.

## Operational notes
- Follow `AGENTS.md` for commands, boundaries, the dependency/supply-chain rules, the
  git workflow, and the source-of-truth order.
- Read `SECURITY.md` before writes, deletes, installs, permission changes, credential
  work, or outbound messages.
- This repo allows third-party dependencies, but only **pinned, locked, and audited**
  (`uv.lock` + `uv audit`). Never add a floating or unused dependency.
- Every harness ships a planted-bug **proof** test. Do not add a harness without one —
  a test that can pass while inert is vacuous green.
- For subagents, tell them to read `AGENTS.md` and `docs/decisions/` first, then report
  verified versus assumed facts.
- Do not edit `.claude/`, hooks, settings, or workflow permissions unless explicitly asked.
- If a push or tool call is blocked, report the exact blocker and the next safe option.
  Do not claim persistence until the remote branch or commit is verified.

## Self-audit before every push (ADR-0002/0003)
Self-initiated, every push: run `/preflight` — `make all` + `tools/audit_drift.py
--strict --run-checks` + the MoE panel (`docs/moe-audit.md`) + a semantic claim-vs-code
review. Zero failures and zero high-severity findings required. The auditor applies safe
fixes only and never alters logic to pass. Mechanics live in `.claude/` (hooks +
`auditor`/`explorer`/`planner` agents + commands), mirrored from `Codex-Speed-Test`.

## Subagent directive
Whenever the Agent tool is used, the agent's prompt MUST tell it to read `AGENTS.md`,
`SECURITY.md`, `docs/decisions/`, and `docs/LEARNINGS.md` first, follow the Working
Agreement (Rule 0 binds subagents too), and append what it learns to `docs/LEARNINGS.md`.
Prefer the predefined roles in `.claude/agents/`. On session start, skim
`docs/LEARNINGS.md` for continuity.
