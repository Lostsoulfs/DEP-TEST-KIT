# 0006 — Mutation testing in CI: advisory, via the mutation_quality harness

Status: accepted (2026-06-14). Records how mutation testing runs in CI and why a full
incremental per-harness mutation gate is deferred.

## Context
The verify+gap pass (`docs/CI_RESEARCH_VERIFICATION_2026-06-14.md`) confirmed from primary
sources that mutation score — not line coverage — is the real signal for the "vacuous
green" failure class this repo exists to guard against (the RMS/PMS-independence and
diversity-aware-adequacy papers verified verbatim; the Gemini doc's "38% AI-generated"
table and the `fest` tool did **not** — both fabricated). The repo already ships a
`mutation_quality` harness (real mutmut, strong-vs-weak suite). Two constraints shape the
gate:
- mutmut 3.x refuses to run on native Windows (boxed/mutmut#397) — Linux/CI/WSL only.
- mutmut 3.x asserts on package-prefixed modules (the "trampoline" issue, `LEARNINGS`
  2026-06-14 Batch 1): it must mutate a TOP-LEVEL module in an isolated dir, which is why
  the harness uses a throwaway temp project. A naive `mutmut run` over the `harnesses/`
  package does not work.

## Decision
- Mutation testing is delivered by the `mutation_quality` harness (the canonical
  vacuous-green detector), run by the per-harness self-tests in `ci.yml` and by
  `make mutation`.
- Add an advisory `Mutation (advisory)` workflow (`mutation.yml`; PR + `workflow_dispatch`;
  Linux; `continue-on-error: true`) as a dedicated, non-blocking lane and a place to grow.
- On Windows the harness and its two mutmut-dependent tests **skip** (`mutmut_available()`
  is False) rather than fail — a real env-skip, never a silent green (mirrors the
  integration lane's Docker-absent skip).
- WSL data point (2026-06-14): the harness self-test runs real mutmut — strong suite kills
  all mutants; weak suite leaves 2 — the teeth gap reproduces on Linux/WSL.
- **Deferred:** a full incremental per-harness mutation gate (mutate each changed harness'
  oracle, run its paired tests) — blocked by the mutmut-3.x package-module trampoline; it
  needs per-file temp-project extraction like the harness already does. Tracked as future
  work, not shipped half-working.

## Consequence
- Mutation signal is present and real, but bounded to the canonical harness for now.
- The advisory lane never blocks merges; promote to required only once an incremental
  per-harness runner exists.
- Local mutation runs need Linux/WSL on a Windows box (documented on `make mutation`).

## Update (2026-06-15) — the deferred per-harness runner now ships, without mutmut
The deferred "mutate each harness' oracle, run its tests" gate is delivered by
`tools/vacuity_gate.py` using a DIFFERENT mechanism that sidesteps the two mutmut blockers:
it monkeypatches each harness's declared `VACUITY_TARGETS` oracle symbol to an inert
stand-in in a subprocess, re-runs the harness's `run_self_test()`, and asserts it goes red
(`TEETH`); a harness that stays green is `VACUOUS` (blocking). Because it never invokes mutmut,
it runs on native Windows and on package-prefixed modules — the exact constraints that blocked
the original plan. The gate proves itself on two fixtures (a real harness that must read TEETH,
a vacuous one that must be detected) via `--self-test`.
- Rollout is **advisory** (`.github/workflows/vacuity.yml`, `continue-on-error`) while
  `VACUITY_TARGETS` is added across all lib+ai harnesses; harnesses without it report `UNMAPPED`.
  Promote to required once no lib+ai harness is `UNMAPPED`.
- `mutation_quality` (the mutmut harness) stays as-is — it remains the real-mutmut signal on
  Linux/WSL; the vacuity gate is the complementary cross-platform per-harness teeth check.
- **Soundness limitation (known, by design):** the inert stand-in returns a unique sentinel, so
  for some harnesses the neutered run goes red via a *type-crash* the moment the sentinel is
  touched (e.g. `sentinel.startswith`), not via the harness's correctness assertion firing. A
  green control run guarantees the redness is caused by the oracle neuter (the only change), so
  the gate soundly proves the oracle symbol is **load-bearing/reachable** — but it does NOT prove
  the self-test would catch every wrong-but-non-crashing oracle, and a self-test that crashed in
  unrelated setup would also read TEETH. This is weaker than true mutation testing (`mutmut`,
  which substitutes plausible non-crashing mutants); the two are complementary. Distinguishing
  "red via assertion" from "red via crash" is possible future work.

## Update (2026-06-16) — rollout complete; lane promoted to required
All lib+ai harnesses now declare `VACUITY_TARGETS` and read TEETH (gate: 20 teeth / 0 vacuous /
0 error / 1 unmapped). The one exception, `mutation_quality`, stays intentionally UNMAPPED — it
env-skips on native Windows, so a mapped target would read VACUOUS locally; its teeth come from the
dedicated `mutation` lane. With no lib+ai harness UNMAPPED (the documented promotion trigger), the
lane was de-advisory'd: `continue-on-error` removed from `vacuity.yml` (job renamed
"Vacuous-green meta-gate", workflow "Vacuity"), `make vacuity` added to `make all`, and the check
added to `main`'s required status checks — so it is now **merge-blocking**. Target-selection note:
the chosen symbol is the one whose neuter makes the self-test go red, which for several harnesses is
the discriminating PREDICATE, not the oracle (the oracle is not always load-bearing in the
self-test) — full rationale in `docs/LEARNINGS.md` (2026-06-15 rollout entry).
