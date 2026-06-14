---
description: Scaffold a new Architecture Decision Record. Usage: /adr <short title>
argument-hint: <short title>
allowed-tools: Bash(ls:*), Read
---

Create a new ADR for: **$ARGUMENTS**

1. Look at `docs/decisions/` to find the next number (zero-padded, e.g. `0004`).
2. Copy `docs/decisions/0000-template.md` to `docs/decisions/<NNNN>-<kebab-title>.md`.
3. Fill in the title, set **Status: proposed** and today's date, and draft the
   Context / Decision / Consequence from what was just discussed.

Keep it concise — one decision, the why, and the trade-offs. Match the style of the
existing ADRs (0001-0003).
