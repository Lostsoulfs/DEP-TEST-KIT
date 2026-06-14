#!/usr/bin/env python3
"""Deterministic PR "drift" auditor for DEP-TEST-KIT.

Ported from Codex-Speed-Test's scripts/audit-drift.mjs and adapted for this repo
(Python sources, ruff, uv/deptry/pytest gates, and the planted-bug-proof invariant —
ADR-0003). No third-party deps, no API key. Compares the LOGGED INTENT (commit
messages, PR body, docs/LEARNINGS.md) against the ACTUAL diff and flags drift. With
--fix it applies only safe, reversible fixes (`ruff format` + `ruff check --fix`, never
--unsafe-fixes). Logic-affecting smells (suppressions, skipped/xfail tests, TODO) are
report-only so the auditor never drifts the code itself.

Usage:
  python tools/audit_drift.py [--base <ref>] [--head <ref>] [--fix]
                              [--run-checks] [--strict] [--history <ndjson>]
                              [--pr-body-file <md>]
Defaults: base=origin/main head=HEAD. Writes audit-report.md + stdout.
Exit 0 always, unless --strict and a high-severity finding exists (then 1); a bad
ref exits 2 (refuse to audit an empty range — the textbook vacuous "no drift").
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLAVORS = ("lib", "integration", "ai")


def sh(cmd: list[str]) -> str:
    try:
        # Force UTF-8 decode: on Windows the default locale codec is cp1252, which
        # crashes on UTF-8 diff content (non-ASCII in docs/code). Linux/CI default UTF-8.
        return subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        ).stdout
    except Exception:
        return ""


def try_ok(cmd: list[str]) -> bool:
    try:
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, check=False).returncode == 0
    except Exception:
        return False


findings: list[dict] = []


def add(id_, sev, conf, title, detail, evidence=None):
    findings.append(
        {
            "id": id_,
            "sev": sev,
            "conf": conf,
            "title": title,
            "detail": detail,
            "evidence": evidence or [],
        }
    )


def ensure_ref(ref: str) -> None:
    if not sh(["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"]).strip():
        sys.stderr.write(
            f"audit: cannot resolve ref '{ref}' — refusing to report on an empty range. "
            "Fetch it (git fetch origin main) or pass a valid --base/--head.\n"
        )
        sys.exit(2)


def parse_added(rng: str) -> list[dict]:
    raw = sh(["git", "diff", "--unified=0", rng, "--", ".", ":(exclude)uv.lock"])
    added: list[dict] = []
    file = None
    new_line = 0
    for line in raw.split("\n"):
        if line.startswith("diff --git"):
            file = None
        elif line.startswith("+++ b/"):
            file = line[6:]
        elif line.startswith("+++ "):
            file = None
        else:
            m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if m:
                new_line = int(m.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                if file:
                    added.append({"file": file, "line": new_line, "text": line[1:]})
                new_line += 1
    return added


def is_code(p: str | None) -> bool:
    return bool(p) and p.endswith(".py")


def in_audit(p: str | None) -> bool:
    # Files allowed to contain the trigger strings (they implement/describe the checks).
    return p in ("tools/audit_drift.py",) or (p or "").startswith("docs/")


def scan(added, id_, pattern, predicate, sev, conf, title, detail):
    rx = re.compile(pattern)
    hits = [a for a in added if predicate(a) and rx.search(a["text"])]
    if hits:
        add(
            id_,
            sev,
            conf,
            title,
            detail,
            [f"{h['file']}:{h['line']}  {h['text'].strip()[:100]}" for h in hits[:12]],
        )


def harness_completeness() -> None:
    """The repo's signature invariant: every harness ships a paired test AND a
    planted-bug proof. A harness without a proof is vacuous-green by construction."""
    for flavor in FLAVORS:
        hdir = ROOT / "harnesses" / flavor
        if not hdir.is_dir():
            continue
        for h in sorted(hdir.glob("*_test_harness.py")):
            name = h.name[: -len("_test_harness.py")]
            paired = ROOT / "tests" / flavor / f"test_{name}_test_harness.py"
            proof = ROOT / "tests" / flavor / f"test_{name}_proof.py"
            missing = [str(p.relative_to(ROOT)) for p in (paired, proof) if not p.exists()]
            if missing:
                add(
                    "harness-incomplete",
                    "high",
                    "high",
                    f"Harness {flavor}/{name} missing test/proof",
                    "Every harness must ship a paired test and a planted-bug proof "
                    "(anti vacuous-green, AGENTS.md / ADR-0001).",
                    missing,
                )


SENSITIVE_RE = re.compile(
    r"^\.github/|^\.claude/|^pyproject\.toml$|^uv\.lock$|^Makefile$|"
    r"^AGENTS\.md$|^CLAUDE\.md$|^SECURITY\.md$|^tools/(scan_staged|audit_drift)\.py$"
)


def read_if(p: str) -> str:
    fp = ROOT / p
    return fp.read_text() if fp.exists() else ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic drift auditor")
    ap.add_argument("--base", default=os.environ.get("AUDIT_BASE", "origin/main"))
    ap.add_argument("--head", default=os.environ.get("AUDIT_HEAD", "HEAD"))
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--run-checks", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--history")
    ap.add_argument("--pr-body-file")
    opt = ap.parse_args(argv)

    ensure_ref(opt.base)
    ensure_ref(opt.head)
    merge_base = sh(["git", "merge-base", opt.base, opt.head]).strip() or opt.base
    rng = f"{merge_base}..{opt.head}"

    name_status = [
        ln.split("\t", 1)
        for ln in sh(["git", "diff", "--name-status", rng]).strip().split("\n")
        if ln
    ]
    changed = [parts[1] for parts in name_status if len(parts) == 2]

    commit_text = sh(["git", "log", "--format=%s%x00%b", rng]).lower()
    pr_body_source = opt.pr_body_file or ".audit/pr-body.md"
    pr_body = (os.environ.get("GITHUB_PR_BODY") or read_if(pr_body_source) or "").lower()
    body_provided = "GITHUB_PR_BODY" in os.environ or (ROOT / pr_body_source).exists()
    claims = f"{commit_text}\n{pr_body}"

    added = parse_added(rng)

    # --- Working-Agreement scans (added lines) --------------------------------
    scan(
        added,
        "lint-suppress",
        r"#\s*(noqa|ruff:\s*noqa|type:\s*ignore)",
        lambda a: is_code(a["file"]) and not in_audit(a["file"]),
        "high",
        "high",
        "Lint/type suppression added",
        "New noqa/ruff:noqa/type:ignore — fix the rule, don't silence it (No silent shortcuts).",
    )
    scan(
        added,
        "test-skip",
        r"@pytest\.mark\.(skip|xfail)|pytest\.skip\(|\.skip\(",
        lambda a: is_code(a["file"]) and a["file"] != "conftest.py" and not in_audit(a["file"]),
        "high",
        "medium",
        "Test skipped / xfailed",
        "A test was skipped or xfailed — gates must not be gutted to pass (No silent shortcuts).",
    )
    scan(
        added,
        "todo-marker",
        r"\b(TODO|FIXME|HACK|XXX)\b",
        lambda a: is_code(a["file"]) and not in_audit(a["file"]),
        "medium",
        "medium",
        "TODO/HACK marker added",
        "Unfinished-work marker introduced — confirm it is intended, not a shortcut.",
    )
    scan(
        added,
        "debug-stmt",
        r"\bbreakpoint\(\)|^\s*import pdb\b",
        lambda a: is_code(a["file"]) and not in_audit(a["file"]),
        "medium",
        "high",
        "Debug statement left in code",
        "Stray breakpoint()/pdb left in a harness or test.",
    )

    # --- repo-state invariants ------------------------------------------------
    harness_completeness()

    sensitive = [p for p in changed if SENSITIVE_RE.search(p)]
    if sensitive:
        add(
            "sensitive-paths",
            "medium",
            "high",
            "Sensitive files changed",
            "Gates/CI/agent-config/deps changed — review intentionality and that it was logged.",
            sensitive,
        )

    harness_changed = any(p.startswith("harnesses/") for p in changed)
    if harness_changed and "docs/LEARNINGS.md" not in changed:
        add(
            "learnings-stale",
            "low",
            "medium",
            "LEARNINGS not updated",
            "harnesses/ changed but docs/LEARNINGS.md was not touched — capture any decision/gotcha.",
        )

    if body_provided and "## deviations from plan" not in pr_body:
        add(
            "deviations-section",
            "medium",
            "high",
            "Deviations section missing",
            'PR body has no "## Deviations from plan" section — required even if "None.".',
        )

    # unlogged files (heuristic): a changed file never named in commits/PR body.
    unlogged = []
    for p in changed:
        if p == "docs/audit-history.ndjson":
            continue
        stem = p.split("/")[-1].rsplit(".", 1)[0].lower()
        if len(stem) > 2 and stem not in claims and p.lower() not in claims:
            unlogged.append(p)
    if unlogged:
        add(
            "unlogged-files",
            "low",
            "low",
            "Possibly unlogged changes",
            "These files are not referenced in any commit message or PR body (heuristic).",
            unlogged[:20],
        )

    # --- optional: gate health -------------------------------------------------
    checks_md = ""
    if opt.run_checks:
        lint = try_ok(["uv", "run", "ruff", "check", "."])
        dep = try_ok(["uv", "run", "deptry", "harnesses"])
        unit = try_ok(["uv", "run", "--frozen", "pytest", "-m", "not integration", "-q"])
        checks_md = (
            "\n## Gate health\n"
            f"- lint (ruff): {'pass' if lint else 'FAIL'}\n"
            f"- deps (deptry): {'pass' if dep else 'FAIL'}\n"
            f"- lib lane (pytest): {'pass' if unit else 'FAIL'}\n"
        )
        if not lint:
            add("lint-fail", "high", "high", "Lint failing", "`ruff check .` failed.")
        if not dep:
            add(
                "deptry-fail",
                "high",
                "high",
                "Dependency scan failing",
                "`deptry harnesses` failed.",
            )
        if not unit:
            add(
                "test-fail",
                "high",
                "high",
                "Lib lane failing",
                "`pytest -m 'not integration'` failed.",
            )

    # --- optional: safe auto-fix ----------------------------------------------
    fix_md = ""
    if opt.fix:
        sh(["uv", "run", "ruff", "format", "."])
        sh(["uv", "run", "ruff", "check", "--fix", "."])
        dirty = sh(["git", "status", "--porcelain"]).strip()
        fix_md = (
            f"\n## Auto-fixes applied\nSafe ruff fixes applied:\n\n```\n{dirty}\n```\n"
            if dirty
            else "\n## Auto-fixes applied\nNone needed — format and lint already clean.\n"
        )

    # --- report ---------------------------------------------------------------
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: order[f["sev"]])
    high = sum(1 for f in findings if f["sev"] == "high")

    md = "## Drift Audit\n\n"
    md += f"Range `{rng}` · {len(changed)} file(s) changed · "
    md += (
        f"**{len(findings)} finding(s)** ({high} high)\n" if findings else "**no drift detected**\n"
    )
    if findings:
        md += "\n| Finding | Severity | Confidence | Evidence |\n|---|---|---|---|\n"
        for f in findings:
            ev = "<br>".join(f"`{e}`" for e in f["evidence"]) if f["evidence"] else f["detail"]
            md += f"| **{f['title']}** | {f['sev']} | {f['conf']} | {ev} |\n"
        md += "\n_Details:_\n"
        for f in findings:
            md += f"- **{f['title']}** (`{f['id']}`) — {f['detail']}\n"
    md += checks_md + fix_md
    md += "\n<sub>Generated by `tools/audit_drift.py` — deterministic, no API key. "
    md += "Semantic claim-vs-code review + the MoE panel happen in the pre-push preflight "
    md += "(docs/moe-audit.md, ADR-0002/0003).</sub>\n"

    (ROOT / "audit-report.md").write_text(md)
    sys.stdout.write(md + "\n")

    if opt.history:
        head_sha = sh(["git", "rev-parse", opt.head]).strip()
        hist = ROOT / opt.history
        prior = hist.read_text() if hist.exists() else ""
        if head_sha and head_sha not in prior:
            line = json.dumps(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "base": merge_base,
                    "head": head_sha,
                    "pr": int(os.environ["GITHUB_PR_NUMBER"])
                    if os.environ.get("GITHUB_PR_NUMBER")
                    else None,
                    "findings": [{"id": f["id"], "sev": f["sev"]} for f in findings],
                }
            )
            with hist.open("a") as fh:
                fh.write(line + "\n")

    if opt.strict and high > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
