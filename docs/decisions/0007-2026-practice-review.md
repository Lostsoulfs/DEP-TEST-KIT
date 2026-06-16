# 0007 — 2026 practice-review: teeth-mechanism soundness + supply-chain hardening

Status: accepted (2026-06-16). Records the decisions from a cited 2026 best-practice review of
the five technique areas this repo uses (oracle-quality/mutation, supply-chain, LLM-output eval,
integration/testcontainers, property-based/metamorphic). The review validated the core
architecture against primary sources and surfaced a small set of concrete gaps; this ADR records
what we decided to change and why. Implementation lands across separate PRs (tracked below).

## Context
A 5-lane web-research pass (2026-06-16) mapped current guidance against our actual practice. The
strong validations (kept as-is, now cited): report-only coverage with **no floor** (a floor
manufactures vacuous green — Inozemtseva & Holmes ICSE 2014; Goodhart); the vacuity gate as a
targeted mutation operator on the oracle; keeping **live LLM judges out of CI** (hosted-API output
is nondeterministic by batch/load — Thinking Machines); assert-by-exception-type (async-wait is the
#1 flakiness cause — Luo et al. FSE 2014); the RBAC reference-model differential; and the
uv-lock/`--frozen` + SHA-pin + zizmor + Renovate-cooldown supply-chain posture.

The review's central finding matched our own retro: **our anti-pattern (vacuous green) can hide
inside our own teeth-mechanisms.** Three were probed; the decisions follow.

## Decision

### D1 — Vacuity-gate stand-in must be TYPE-COMPATIBLE (was: inert sentinel)
The gate currently replaces an oracle symbol with an inert stand-in returning a unique sentinel.
For some harnesses the resulting red comes from a **type-crash** when the sentinel is touched
(e.g. `sentinel > 0`), not from the harness's assertion firing. In mutation terms that is a
trivial/unproductive mutant: it proves the oracle is *reachable*, not that the self-test *asserts
the right thing*. **Decision:** the stand-in returns a plausible-but-wrong value of the oracle's
real return **type** (flip a bool, off-by-one an int, empty-but-valid container), so red can only
come from the assertion. This converts the gate from a reachability check into a true
oracle-strength check, and will EXPOSE any harness that was only passing via crash (→ strengthen
that self-test to assert the value). Implementation: PR `feat/vacuity-type-compatible-sentinel`.

### D2 — Mutation lane VERIFIED real (no code change)
Concern: mutmut can silently no-op on a platform without fork support ("green without mutants").
**Verified** from CI run 27586706631 (2026-06-16): `mutmut==3.6.0`,
`self-test: OK (strong suite kills all; weak suite leaves 2 mutant(s) alive)` — mutmut genuinely
forks and evaluates mutants on Linux CI, with real survivor counts. The native-Windows skip is the
only degraded path and is by-design (env-skip, ADR-0006). **Decision:** no change; keep surfacing
survivor counts as the signal; re-verify after any mutmut major bump.

### D3 — Supply-chain: add the layers `uv audit` cannot cover
`uv audit` scans OSV **CVEs**; it does not catch a freshly-published malicious package with no
advisory yet (the 2026 LiteLLM / `.pth`-import-execution class), and a Renovate cooldown only
delays *PR creation*, not a `uv lock` pulling a new compromised transitive. **Decision:** add
(a) install-time malware screening (uv `UV_MALWARE_CHECK` / OSV `MAL` advisories), (b) a
lockfile-layer cooldown (`[tool.uv] exclude-newer`) with a documented CVE-fix break-glass,
(c) an explicit CI check of `uv audit`'s exit code (it is a preview tool — do not assume it fails
the build), and (d) keep a vendor-independent OSV fallback (`pip-audit`/`osv-scanner`) given the
all-Astral concentration (Astral→OpenAI, 2026). Implementation: PR `feat/supply-chain-hardening`.

## Accepted direction (tracked in HARNESS_ROADMAP Backlog, not yet scheduled)
- **AI lane honesty + teeth:** name deterministic scorers as narrower *proxies* (not "Faithfulness"
  / "G-Eval" — avoid implying RAGAS/DeepEval equivalence); ensure each metamorphic relation *can*
  fail (stability-by-construction is vacuous; stability ≠ correctness — consistent-hallucination
  false negatives); `judge_reliability` unanimity proves stability not validity → add a bias probe
  (order-swap/verbosity) + justify the 12-char span threshold; add positive/negative fixtures so the
  scorers provably separate faithful from unfaithful.
- **Property-based:** RBAC is stateful → adopt Hypothesis `RuleBasedStateMachine` (op-sequences vs
  the reference model, `@invariant`); use `hypothesis.target()` for rare states; add
  exception/precondition-violation properties (OOPSLA 2025: ~113× more effective, ~10% used); gate
  agent-inferred properties with property-mutants (agentic-PBT false-discovery 30–57%).
- **Integration:** migrate off the deprecating `wait_for_logs` decorator to `WaitStrategy` /
  `ExecWaitStrategy`; prefer HEALTHCHECK over brittle log-string waits; verify started-vs-ready for
  Kafka/ES/Vault/Keycloak; add a flaky-test detection/quarantine lifecycle.
- **SBOM:** sign/attest + attach the CycloneDX SBOM (not just generate it) on a current spec version.

## Consequence
- The vacuity gate (our flagship) becomes a real oracle-strength check; expect it to flag
  previously crash-passing harnesses, which is the intended surfacing of latent vacuity.
- The supply-chain gate gains the malware/zero-day-cooldown layer the 2026 incident wave exploited.
- The unifying principle going forward: **every teeth-mechanism must itself be teeth-checked**
  (type-compatible mutants, property-mutants, positive/negative fixtures, capture the score not just
  "it ran").

## Sources (primary, cited in the review)
- Inozemtseva & Holmes, "Coverage Is Not Strongly Correlated with Test Suite Effectiveness" (ICSE 2014): <https://www.cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf>
- "Mind the Gap: ... Coverage and Mutation Score" (arXiv 2309.02395): <https://arxiv.org/abs/2309.02395>
- mutmut docs (fork/WSL requirement): <https://mutmut.readthedocs.io/en/latest/index.html>
- Astral — open-source security at Astral (uv cooldown, malware check, attestations): <https://astral.sh/blog/open-source-security-at-astral>
- Datadog — LiteLLM compromised on PyPI (TeamPCP): <https://securitylabs.datadoghq.com/articles/litellm-compromised-pypi-teampcp-supply-chain-campaign/>
- Thinking Machines — Defeating Nondeterminism in LLM Inference: <https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/>
- RAGAS — Faithfulness (LLM vs HHEM) / Context Precision (NonLLM): <https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/>
- Luo et al., "An Empirical Analysis of Flaky Tests" (FSE 2014): <https://philmcminn.com/publications/parry2021.pdf>
- testcontainers-python releases (WaitStrategy migration): <https://github.com/testcontainers/testcontainers-python/releases>
- Ravi & Coblenz, "An Empirical Evaluation of Property-Based Testing in Python" (OOPSLA 2025): <https://cseweb.ucsd.edu/~mcoblenz/assets/pdf/OOPSLA_2025_PBT.pdf>
- "Can LLMs Write Good Property-Based Tests?" (arXiv 2307.04346): <https://arxiv.org/pdf/2307.04346>
