# 0004 — Audit history via CI artifacts, never a pushed file

Status: accepted (2026-06-14). Records how the Drift Audit collects the longitudinal
history that `/audit-retro` consumes, after two pushing designs failed in this
environment.

## Context
`/audit-retro` needs a per-PR history of auditor findings (≥5 PRs) to judge fire-rates.
Two designs that write `docs/audit-history.ndjson` were tried and abandoned:

1. **Push to the PR head** (auto-fix + history committed to the PR branch). In this
   environment, GITHUB_TOKEN pushes create approval-**held** runs; the required status
   checks on the bot-commit head never complete, so the PR cannot merge
   ("4 of 4 required status checks are expected").
2. **Push to `main` on merge** (commit history with `[skip ci]`). `main` is a protected
   branch (PR + required checks), so the bot push is rejected outright:
   `! [remote rejected] main -> main (protected branch hook declined)`. Every post-merge
   `history` run failed; the file never grew past its one stale entry.

Both were surfaced by `/audit-retro` itself (it found 1 run / 1 PR and the failing runs).

## Decision
The Drift Audit workflow **never pushes**. On each PR run it:
- posts the report as a PR comment (report-only), and
- writes this run's single history line and uploads it as a build artifact
  `audit-history-<run_id>` (90-day retention).

`/audit-retro` aggregates the recent `audit-history-*` artifacts (list Drift Audit runs
→ download each run's artifact → concatenate) instead of reading a committed file. There
is no committed `docs/audit-history.ndjson`; the workspace file is git-ignored.

## Consequence
No interaction with branch protection or held runs — PRs stay mergeable and history
accrues reliably, one artifact per PR run. Cost: history is bounded by artifact
retention (90 days) and must be gathered via the Actions API rather than `cat` on a
file. `/audit-retro` stays propose-only (ADR-0003); this ADR only changes where its
input comes from.
