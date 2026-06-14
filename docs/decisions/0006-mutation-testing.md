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
