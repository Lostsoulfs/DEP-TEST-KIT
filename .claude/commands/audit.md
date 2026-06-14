---
description: Run the drift audit on the current branch (report only).
allowed-tools: Bash(uv run python tools/audit_drift.py:*), Bash(git fetch:*)
---

Fetch `origin/main`, then run the drift auditor against the current branch and
summarize the findings:

```
git fetch origin main --quiet
uv run python tools/audit_drift.py --base origin/main --head HEAD --run-checks
```

Report the findings concisely (severity + what needs attention). Do not auto-fix
unless asked. The pre-push version is `/preflight`, which runs it `--strict` and adds
the MoE panel + semantic review (ADR-0002/0003).
