#!/usr/bin/env python3
"""Render a local static reviewer dashboard from STATUS.json."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

DEFAULT_SCOPE = (
    "current proof baseline; fixture-defined proof under current tooling; "
    "does not claim total correctness or production assurance"
)


def e(value: object) -> str:
    return escape(str(value), quote=True)


def load_status(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def counts(status: dict[str, Any]) -> dict[str, int]:
    raw = status.get("counts", {})
    items = status.get("harnesses", [])
    return {
        "harnesses": int(raw.get("harnesses", len(items))),
        "lib": int(raw.get("lib", sum(1 for item in items if item.get("flavor") == "lib"))),
        "integration": int(
            raw.get("integration", sum(1 for item in items if item.get("flavor") == "integration"))
        ),
        "ai": int(raw.get("ai", sum(1 for item in items if item.get("flavor") == "ai"))),
        "teeth_verified": int(raw.get("teeth_verified", 0)),
        "teeth_eligible": int(raw.get("teeth_eligible", 0)),
        "exceptions": int(raw.get("exceptions", 0)),
    }


def card(item: dict[str, Any]) -> str:
    title = item.get("id") or item.get("name") or "unknown"
    flavor = item.get("flavor", "unknown")
    status = item.get("status", "unknown")
    proof_type = item.get("proof_type", "proof source")
    teeth = item.get("teeth_state", "unknown")
    summary = item.get("summary") or item.get("why") or "No summary supplied."
    source_files = item.get("source_files", [])
    commands = item.get("commands", [])
    source_html = "".join(f"<li><code>{e(path)}</code></li>" for path in source_files)
    command_html = "".join(f"<li><code>{e(command)}</code></li>" for command in commands)
    return f"""
<article class="card" data-flavor="{e(flavor)}" data-status="{e(status)}" data-proof="{e(proof_type)}" data-teeth="{e(teeth)}">
  <div class="card-head">
    <h3>{e(title)}</h3>
    <div class="badges"><span>{e(flavor)}</span><span>{e(status)}</span><span>{e(teeth)}</span></div>
  </div>
  <p>{e(summary)}</p>
  <h4>Source files</h4>
  <ul>{source_html}</ul>
  <h4>Commands</h4>
  <ul>{command_html}</ul>
  <h4>Next test path</h4>
  <p>{e(item.get('next_test_path', 'Extend around the same contract without overclaiming.'))}</p>
</article>
"""


def render(status: dict[str, Any]) -> str:
    c = counts(status)
    generated = status.get("generated_at") or datetime.now(timezone.utc).isoformat()
    scope = status.get("claim_scope") or DEFAULT_SCOPE
    items = status.get("harnesses", [])
    cards = "\n".join(card(item) for item in items)
    teeth = f"{c['teeth_verified']}/{c['teeth_eligible']}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DEP-TEST-KIT Reviewer Dashboard</title>
<style>
:root {{ color-scheme: light; --ink: #071426; --muted: #53627a; --line: #d7e0ea; --accent: #007c89; --bg: #f5f8fb; --panel: #ffffff; }}
body {{ margin: 0; font: 16px/1.5 system-ui, sans-serif; background: var(--bg); color: var(--ink); }}
main {{ max-width: 1280px; margin: 0 auto; padding: 48px 24px; }}
.hero, .card, .panel, .stat {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; box-shadow: 0 16px 40px rgba(8, 26, 46, .05); }}
.hero {{ display: grid; grid-template-columns: 1fr 320px; gap: 24px; padding: 24px; }}
h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 3.2rem); line-height: 1; }}
.kicker, h4 {{ color: var(--accent); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }}
.stats {{ display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap: 12px; margin: 24px 0; }}
.stat {{ padding: 18px; }} .stat strong {{ display: block; color: var(--accent); font-size: 2rem; }}
.scope {{ border-left: 5px solid var(--accent); background: #e8f8fa; padding: 16px; border-radius: 8px; }}
.panel {{ padding: 18px; margin: 20px 0; }}
.filters {{ display: grid; grid-template-columns: 2fr repeat(3, 1fr); gap: 12px; }}
input, select {{ width: 100%; box-sizing: border-box; padding: 12px; border: 1px solid var(--line); border-radius: 8px; font: inherit; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }}
.card {{ padding: 18px; }} .card-head {{ display: flex; justify-content: space-between; gap: 16px; }}
.badges {{ display: flex; gap: 6px; flex-wrap: wrap; }} .badges span {{ background: #e9f7ef; border-radius: 999px; padding: 3px 8px; font-size: .85rem; }}
code {{ background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }}
@media (max-width: 800px) {{ .hero, .filters, .stats {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main>
<section class="hero">
  <div><div class="kicker">DEP-TEST-KIT reviewer dashboard</div><h1>Pick a proof path, then use the harness</h1><p>A local static portal for humans and AI agents to find the right dependency-backed harness without overclaiming.</p></div>
  <aside><strong>Generated</strong><br>{e(generated)}<br><br><strong>Status</strong><br>{e(status.get('source', {}).get('mode', 'STATUS.json'))}</aside>
</section>
<section class="stats">
  <div class="stat"><strong>{c['harnesses']}</strong>Harnesses</div><div class="stat"><strong>{c['lib']}</strong>Lib</div><div class="stat"><strong>{c['integration']}</strong>Integration</div><div class="stat"><strong>{c['ai']}</strong>AI</div><div class="stat"><strong>{e(teeth)}</strong>TEETH</div><div class="stat"><strong>{c['exceptions']}</strong>Exceptions</div>
</section>
<p class="scope">Claim scope: {e(scope)}.</p>
<section class="panel filters"><input id="q" placeholder="Search harnesses, failure classes, commands"><select id="flavor"><option value="">All flavors</option><option>lib</option><option>integration</option><option>ai</option></select><select id="status"><option value="">All statuses</option></select><select id="teeth"><option value="">All TEETH states</option></select></section>
<h2>Harness map</h2><p id="shown">{len(items)} of {len(items)} harnesses shown</p><section class="grid" id="cards">{cards}</section>
</main>
<script>
const q = document.getElementById('q');
const flavor = document.getElementById('flavor');
const shown = document.getElementById('shown');
const cards = [...document.querySelectorAll('.card')];
function apply() {{
  const term = q.value.toLowerCase();
  let count = 0;
  for (const card of cards) {{
    const ok = (!term || card.textContent.toLowerCase().includes(term)) && (!flavor.value || card.dataset.flavor === flavor.value);
    card.hidden = !ok; if (ok) count += 1;
  }}
  shown.textContent = `${{count}} of ${{cards.length}} harnesses shown`;
}}
q.addEventListener('input', apply); flavor.addEventListener('change', apply);
</script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path, default=Path("STATUS.json"))
    parser.add_argument("--output", type=Path, default=Path("dashboard/site/index.html"))
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.status.exists():
        print(f"missing {args.status}; run make report first", file=sys.stderr)
        return 2
    html = render(load_status(args.status))
    if args.check:
        if args.output.exists() and args.output.read_text(encoding="utf-8") != html:
            print(f"stale dashboard: regenerate {args.output}", file=sys.stderr)
            return 1
        with TemporaryDirectory() as tmp:
            Path(tmp, "index.html").write_text(html, encoding="utf-8")
        print("dashboard check ok")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
