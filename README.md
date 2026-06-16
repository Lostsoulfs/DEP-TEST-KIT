# DEP-TEST-KIT

Dependency-backed and real-service **integration** test harnesses — the non-stdlib
companion to [`testing-kits`](https://github.com/lostsoulfs/testing-kits).

`testing-kits` is deliberately zero-dependency, pure-stdlib. This repo is the
opposite by design: small, inspectable harnesses that demonstrate a real failure
class **using the right third-party tool or a real ephemeral service** — pinned,
locked, and audited. Same shape as testing-kits; different dependency rule.

## Three flavors

| Flavor | Path | Runs | Needs |
|--------|------|------|-------|
| **lib** | `harnesses/lib/` | in-process | a pinned library (e.g. Hypothesis, pydantic) |
| **integration** | `harnesses/integration/` | real ephemeral service | Docker + testcontainers |
| **ai** | `harnesses/ai/` | in-process, deterministic | a pinned library (deepeval / Hypothesis); **no live LLM, no API key** |

## The harness shape (every file explains itself)

One self-contained harness + a paired test + a planted-bug **proof** test. Every
harness documents, in its module docstring:

- **WHY** — the failure class it catches that the stdlib / example-based tests miss.
- **HOW** — the dependency or service, the correct **oracle**, and the intentional
  **buggy** implementation it proves it catches.
- **WHERE** — which flavor, and the dependency it adds to the matching `pyproject` extra.

The proof test is non-negotiable: it asserts the buggy impl is caught and the oracle
passes. A test that can pass while inert is *vacuous green* — the bug class this repo
exists to prevent.

## What's here

**32 harnesses** (15 lib / 11 integration / 6 ai). See `HARNESS_INVENTORY.md` for the full list
with WHY/HOW/WHERE per harness, and `HARNESS_ROADMAP.md` for what's next. A few examples:

- `lib/property_roundtrip` — Hypothesis round-trip property; shrinks a planted
  single-run-dropping decoder to a 2-char counterexample.
- `lib/hallucinated_dependency` — resolves a pinned `name==version` against the live installed
  environment; catches a hallucinated version of a real package that a naive name-only check misses.
- `integration/postgres_store` — asserts a real `UNIQUE` constraint on an ephemeral PostgreSQL;
  proves a store that forgot it silently writes duplicates (a mock catches neither).
- `ai/llm_eval` — deterministic hallucination detection (a deepeval `BaseMetric`), no live model.

## No vacuous green — the meta-gate

Every lib+ai harness declares a `VACUITY_TARGETS` oracle symbol. `tools/vacuity_gate.py` neuters
each one in a subprocess and re-runs the harness's self-test, asserting it goes **red** (`TEETH`);
a harness that stays green with its oracle gutted is `VACUOUS` and fails the gate. It runs in CI as
a **required** check (`make vacuity`), so a harness cannot land — or rot into — a test that passes
while inert. (`mutation_quality` is intentionally exempt: mutmut can't run on native Windows, so its
teeth come from the dedicated `mutation` lane instead.)

## Running

```bash
uv sync --all-extras                 # provision a locked, reproducible env
uv run pytest -m "not integration"   # fast lib lane (no Docker)
uv run pytest -m integration         # real-service lane (needs Docker)
uv run python harnesses/lib/property_roundtrip_test_harness.py --self-test
```

## Dependency policy

Dependencies are allowed, but **pinned, locked (`uv.lock`), and audited**. CI fails on
unlocked, unused, or vulnerable dependencies (`uv sync --locked` → `deptry` → `uv audit`
→ `uv run --frozen`). A dependency is added to `pyproject.toml` only when a harness
actually imports it. See `docs/decisions/0001-stack-decisions.md` for why each tool was
chosen.

See `AGENTS.md` for the working contract and `HARNESS_ROADMAP.md` for what's next.
