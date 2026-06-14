---
description: Preflight, commit, push, ensure the draft PR exists, start babysitting CI. Usage: /ship <commit message>
argument-hint: <commit message>
allowed-tools: Bash(make:*), Bash(uv run:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(git status:*), Bash(git fetch:*)
---

Ship the current work (AGENTS.md git/PR workflow):

1. Run the **/preflight** gate in full (gates + drift audit + MoE panel + semantic
   self-review). If anything fails: stop, fix, re-run — never skip a step to make it pass.
2. If clean: `git add -A`, commit with this message — `$ARGUMENTS` — and
   `git push -u origin <current-branch>`.
3. Ensure a **draft PR** exists for the branch (create it if not, via the GitHub MCP
   tools in remote sessions), with the gate/audit summary in `## Self-audit` and
   `## Deviations from plan` filled honestly.
4. Subscribe to PR activity and babysit CI to green: diagnose and fix failures
   autonomously, re-preflight before each fix push.
5. Report state to the operator. **Never merge** — the merge call is the operator's.
