# 0001 — Stack & convention decisions

Status: accepted (2026-06-14). This records *why* DEP-TEST-KIT is built the way it is,
so harnesses and contributors don't re-litigate settled choices. Grounded in four 2026
deep-research reports (kept in the owner's Drive):

- **T1** — Python testing-library ecosystem survey
- **T2** — Python CI integration testing approaches
- **T3** — advanced fuzzing & AI testing strategies
- **T6** — Python dependency management & security

## Context
`testing-kits` is intentionally zero-dependency stdlib. There was "enough of that
category." DEP-TEST-KIT is its sibling for tests that *need* a real dependency or a
real service, kept to the same harness shape but with a different dependency rule.
A separate repo (not a subtree of testing-kits) keeps testing-kits' "zero runtime
dependencies" promise intact and isolates the supply-chain maintenance.

## Decisions

### Dependency manager: uv (T6)
uv gives a cross-platform hash-pinned `uv.lock`, fast installs, and strict CI
primitives: `uv sync --locked` fails on manifest/lock drift and `uv run --frozen`
refuses to mutate the environment mid-run. The lockfile **is** committed.

### Update automation: Renovate, not Dependabot (T6)
Dependabot does not parse `uv.lock`'s transitive graph and goes blind to deep
vulnerabilities. Renovate has native uv support, `lockFileMaintenance` for transitive
refresh, and `minimumReleaseAge` to honor a release-age cooldown against takeovers.

### Vulnerability audit: `uv audit` (T6)
Native OSV-backed scan of the locked graph; verified available in the pinned uv. CI
fails on any CVE in the direct or transitive graph.

### Unused-dependency gate: deptry (T6)
A declared-but-unimported dependency is attack surface. deptry (scanning `harnesses/`)
fails the build on unused/missing deps, which is why a dependency is added only when a
harness imports it.

### Supply-chain hardening (T6)
GitHub Actions pinned to **full commit SHAs** (not tags — prevents tag-renaming
attacks); least-privilege `permissions: contents: read`; CycloneDX SBOM generated and
uploaded each run; `zizmor` statically audits the workflows. (This is the operational
twin of testing-kits' `ci_workflow_hardening` harness.)

### lib-flavor seeds (T1)
T1's "build first" ranking drives the lib roadmap (Hypothesis, then pydantic+polyfactory,
respx, time-machine, schemathesis, mutmut). The scaffold ships Hypothesis as the first
seed because property-based round-trip is the clearest demonstration of "generated
inputs + shrinking" beating example-based tests.

### integration pattern: testcontainers + pytest-xdist (T2)
T2 rejects Docker Compose (the ~8-min "integration tax") and GitHub Actions service
containers (rigid, no programmatic lifecycle) for the CI suite. Standard: session-scoped
testcontainers, `ryuk` cleanup, dynamic ephemeral ports, `WaitStrategy` over sleeps.
Isolation: relational → `autocommit=False` + teardown ROLLBACK; NoSQL/Redis → logical
namespacing per `worker_id`. PostgreSQL runs with `fsync=off`/`synchronous_commit=off`
for ~50% faster tests (CI-only; never production). The Postgres seed implements exactly
this.

### T3 scope boundary
T3's frontier fuzzers (MuoFuzz, MendelFuzz, TYPEFUZZ, SYSYPHUZZ, Gordian) target
C/kernel/JIT internals and SMT+LLM hybrids — not pip-installable Python harness material.
The one portable thread is **agentic property-based testing** (LLM-authored Hypothesis
tests), parked under the future `ai/` flavor. Note: T3's "mutation" means *fuzzer input
mutation*, distinct from T1's *test-suite mutation testing* (mutmut) — they are not the
same gate.

## Addendum — ported dependency additions (2026-06-22)
The `dep-kit-local-ref` port (46 harnesses; see `HARNESS_ROADMAP.md` and ADR-0008) added 14
dependency declarations, each only because a shipped harness imports it (deptry-enforced). They
follow the established rule: a `>=` **floor** in `pyproject` (CVE floor where relevant) + exact
pin in `uv.lock`.

- **lib** += `werkzeug` (safe_join), `jsonschema` (schema contracts), `idna` (host
  canonicalization), `requests` (header-validity / fail-closed authz), `jinja2`
  (autoescape / SSTI sandbox), `graphql-core` (depth limit), `defusedxml` (XXE),
  `pyyaml` (deserialization), `nh3` (HTML sanitization), `ldap3` (LDAP-filter escaping),
  `python-magic` (content-type by magic bytes).
- **ai** += `simpleeval` (expression sandbox), `pybreaker` (agent circuit breaker),
  `cryptography` (already a lib dep; now also declared for the ai extra's signing harnesses).

Two deliberate substitutions/limits, recorded so they aren't re-litigated:
- **nh3, not bleach** — `bleach` is end-of-life; `nh3` (ammonia/Rust) is the maintained
  allow-list HTML sanitizer.
- **`python-magic` is platform-gated** — libmagic hangs under python-magic on native Windows,
  so `file_upload_validation` imports it lazily and skips its self-test on Windows (CI/Linux runs
  it), the same env-skip pattern as the `mutmut` lane; it is vacuity-exempt for that reason.
- **CVE floors applied at add time:** `werkzeug>=3.0.6` (CVE-2024-49766), `idna>=3.15`
  (CVE-2026-45409), `requests>=2.32.4` (CVE-2024-47081).

## Consequence
The anti-goal is **vacuous green**: a test/gate/proof that passes while inert. Every
harness ships a planted-bug proof; CI gates only ever strengthen.
