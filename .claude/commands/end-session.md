---
description: End-of-session sweep — check state + drift, surface every open loop, act on the operator's calls, then go read-only and write a chat-only diary. Usage: /end-session
allowed-tools: Bash(git status:*), Bash(git fetch:*), Bash(git log:*), Bash(git branch:*), Bash(git diff:*), Bash(make:*), Bash(uv run:*), Read, Grep, Glob
---

Run the end-of-session protocol — a STOP-AND-RECONCILE ritual. Only run it on an
explicit "end session" / `/end-session`.

## 1. Check state of everything + drift sweep
- Open PRs and their CI conclusions on the real code commit (bot `audit:` commits may
  not retrigger CI — check the last code commit).
- Working branch vs `main`; orphaned/unmerged branches; uncommitted work; unpushed
  commits (this container is ephemeral — unpushed = lost).
- A drift pass: `uv run python tools/audit_drift.py --base origin/main --head HEAD`;
  stale claims, wrong numbers, evidence-level overclaims ("CI green" off a local run),
  preflights skipped.

## 2. Close every open question
Resolve every dangling question by asking the operator (AskUserQuestion) so nothing is
left as a silent todo. What's reserved for the operator: merges, scope calls.

## 3. List it all for the operator to audit
One scannable list — PRs (state + CI), branches, open loops, drift findings, any
security flags. Surface, don't decide.

## 4. Do whatever the operator says
Act on the calls. **Merges are theirs alone — never merge.** Work not from this session
is surfaced, never touched without say-so.

## 5. Only AFTER the final push, switch to READ-ONLY
No more repo writes/commits/pushes. Then write the session diary in chat only — never a
committed JOURNAL/handoff file (persistence is the repo + PRs).
