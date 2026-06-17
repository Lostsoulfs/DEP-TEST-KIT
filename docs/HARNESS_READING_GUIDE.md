# Harness Reading Guide

Purpose: make the dependency-backed harness repo readable by humans first and easy for AI agents to navigate later, without expanding `AGENTS.md` into a long context file.

This document is descriptive. It is **not** an instruction override. For operating rules, use `AGENTS.md`, `CLAUDE.md`, and `SECURITY.md`.

## Reader layers

Use the smallest layer that answers the question.

| Layer | Best for | Files |
| --- | --- | --- |
| 0. Orientation | Fast understanding of repo purpose and dependency boundary | `README.md` |
| 1. Rules | Safe operation before edits | `AGENTS.md`, `CLAUDE.md`, `SECURITY.md` |
| 2. Decisions | Why the stack and gates exist | `docs/decisions/`, `docs/moe-audit.md` |
| 3. Inventory | Finding an existing harness and avoiding duplicates | `HARNESS_INVENTORY.md`, `HARNESS_ROADMAP.md` |
| 4. Proof model | Understanding whether a harness actually bites | paired proof tests, `tools/vacuity_gate.py`, `tools/gate_canary.py`, `docs/LEARNINGS.md` |
| 5. Implementation | Reading or modifying one harness | `harnesses/<flavor>/<name>_test_harness.py`, paired `tests/<flavor>/test_<name>_test_harness.py`, paired proof file |
| 6. Supply chain | Maintaining dependency integrity | `pyproject.toml`, `uv.lock`, `Makefile`, `.github/workflows/`, `tools/control_audit.py` |

## Human reading path

For a reviewer:

1. Read `README.md` to understand the lib / integration / ai split.
2. Read `HARNESS_INVENTORY.md` to choose a harness.
3. Open the harness file, paired test, and proof test.
4. Run the smallest relevant command first:
   - one harness: `uv run --frozen python harnesses/<flavor>/<name>_test_harness.py --self-test`
   - fast lane: `uv run --frozen pytest -m "not integration" -q`
   - real-service lane: `uv run --frozen pytest -m integration -q`
   - full mechanical preflight: `make all`
5. Use `docs/LEARNINGS.md` only for gotchas and historical context. Do not treat it as canonical if live code disagrees.

For the maintainer:

1. Classify the change: harness logic, docs, gate machinery, dependency graph, or workflow/control policy.
2. For harness logic, require paired tests, planted-bug proof, and vacuity evidence where applicable.
3. For dependency changes, verify direct import, `pyproject.toml`, `uv.lock`, deptry, and audit behavior.
4. For gate machinery, run `make canary`, `make guard`, and the specific gate being changed.
5. For integration harnesses, keep Docker/service readiness assumptions explicit.

## AI reading path

For AI agents, the expected retrieval order is:

1. `AGENTS.md`, `CLAUDE.md`, `SECURITY.md` for operating boundaries.
2. `llms.txt` for the compact navigation map.
3. `README.md` for public repo shape.
4. `HARNESS_INVENTORY.md` and `HARNESS_ROADMAP.md` to avoid duplicate harness work.
5. `docs/decisions/` when dependency, gate, CI, or supply-chain choices are involved.
6. The specific harness + paired test + proof test for the actual task.
7. `docs/LEARNINGS.md` only after locating the relevant area.

Do not load every document by default. Broad loading increases stale-context risk and makes agents more likely to follow historical notes over live code.

## Harness dossier shape

When documenting or auditing a harness, capture these fields. Keep them factual and compact.

```text
Name:
Path:
Flavor: lib | integration | ai
Dependency / service:
Failure class:
Oracle / load-bearing predicate:
Planted mutant(s):
Corpus / fixtures:
Proof file:
Vacuity target(s): none | symbol list | intentionally unmapped
Commands:
Known limits:
Nearest related harnesses:
```

Use this structure in future inventory expansions, PR summaries, or per-harness docs. Do not duplicate full source code into docs.

## Expansion policy

Good expansion:

- Explains why a dependency or real service is needed.
- Explains the bug class, oracle, planted mutant, and proof path.
- Separates fast in-process harnesses from Docker-backed integration harnesses.
- Links to source files instead of restating implementation.
- Marks unverified counts as loaded state, not fresh proof.

Bad expansion:

- Adds new behavioral rules outside `AGENTS.md`.
- Turns README into a full manual.
- Adds a dependency because it is interesting rather than imported by a harness.
- Treats deterministic AI-lane proxies as live LLM evaluation.
- Claims a gate is required before verifying the exact CI context / branch-protection state.
- Treats historical `docs/LEARNINGS.md` entries as current truth without checking live files.

## Current next layer

The next useful layer is a per-harness dossier index derived from `HARNESS_INVENTORY.md` plus live vacuity/proof status. Build it as a generated or mechanically checkable artifact if possible; avoid hand-maintaining counts that can drift.
