# Harness Roadmap

Forward-looking companion to `HARNESS_INVENTORY.md`. Candidates are grounded in the
2026 research captured in `docs/decisions/0001-stack-decisions.md`. Each new harness
adds its dependency to the matching `pyproject` extra **only when built** (deptry gates
unused declarations), and ships a planted-bug proof test.

## Shipped
- Batch 0 (scaffold): `lib/property_roundtrip` (Hypothesis), `integration/postgres_store`
  (testcontainers + psycopg).
- Batch 1 (lib) — **complete**: `lib/schema_validation` (pydantic + polyfactory),
  `lib/async_http_contract` (respx + httpx), `lib/temporal_logic` (time-machine),
  `lib/mutation_quality` (mutmut), `lib/openapi_fuzz` (schemathesis + flask).
- Batch 2 (integration) — **complete**: `redis_cache`, `kafka_stream`, `mysql_store`,
  `mongo_store`, `object_store` (all testcontainers).
- Batch 3 (ai) — **complete**: `agentic_pbt` (hypothesis), `llm_eval` (deepeval).
- Standalone: `integration/network_chaos` (Toxiproxy + redis) — missing socket-timeout
  under a stalled upstream.
- Batch 4 lib (security-leaning) — **complete**: `crypto_correctness` (cryptography),
  `secret_scanning` (detect-secrets), `sql_orm` (sqlalchemy), `retry_resilience` (tenacity).
- Batch 4 integration (security-leaning) — **complete**: `vault_secrets` (hvac),
  `elasticsearch_index` (elasticsearch), `rabbitmq_redelivery` (pika), `keycloak_oidc` (pyjwt).
- Batch 5 (ai) — **complete**: `rag_faithfulness` (deepeval, context precision),
  `geval_rubric` (deepeval, deterministic rubric grader), `metamorphic_stability` (hypothesis).
- Batch 6 (lib, auth) — **complete**: `jwt_alg_confusion` (pyjwt[crypto], algorithm-confusion
  rejection / proves the >=2.13 floor), `rbac_authz_differential` (hypothesis, model-based
  authorization differential).
- Batch 7 (ai) — **complete**: `judge_reliability` (deepeval, LLM-judge variance gate +
  verbatim-span citation predicate).
- Batch 8 (lib) — **complete**: `hallucinated_symbol` (pydantic, live-surface attribute
  resolution vs a naive module-only check).
- Batch 9 (lib) — **complete**: `hallucinated_dependency` (packaging, live installed-version
  resolution vs a naive name-only check), `prompt_cache_prefix` (pydantic, volatile content in
  the cached prompt prefix vs a naive breakpoint-exists check).

## Batch 1 — lib (library-backed, in-process) ✅ complete
Source: research T1 (testing-library ecosystem survey).

| Candidate | Dep | Failure class | Status |
|-----------|-----|---------------|--------|
| `schema_validation` | pydantic + polyfactory | poison-payload / nested-type drift; polyfactory exhausts Union/Enum variants | ✅ shipped |
| `async_http_contract` | respx | async connection-pool / retry / timeout flaws on httpx clients | ✅ shipped |
| `temporal_logic` | time-machine | C-extension-safe time freezing (expiry, schedulers) | ✅ shipped |
| `openapi_fuzz` | schemathesis | OpenAPI/GraphQL contract drift, server 500s (in-process WSGI runner) | ✅ shipped |
| `mutation_quality` | mutmut | vacuous green — code executed by coverage but not asserted (CLI runner) | ✅ shipped |

## Batch 2 — integration (real ephemeral services) ✅ complete
Source: research T2 (CI integration testing). Each follows the testcontainers +
`pytest-xdist` pattern; isolation per service as noted.

| Candidate | Service | Isolation | Status |
|-----------|---------|-----------|--------|
| `redis_cache` | Redis | logical DB-index per xdist worker | ✅ shipped |
| `kafka_stream` | Kafka (KRaft) | per-test topic + consumer group | ✅ shipped |
| `mysql_store` | MySQL | DROP+CREATE per test (DDL auto-commits) | ✅ shipped |
| `mongo_store` | MongoDB | per-worker logical database | ✅ shipped |
| `object_store` | MinIO (S3) | per-test bucket | ✅ shipped |

Deviations from the original plan: `mysql_store` uses DROP+CREATE rather than
`initdb.d` seed + rollback (MySQL DDL auto-commits, so rollback can't undo a table);
`mongo_store` uses sync `pymongo` rather than async Motor (no event-loop complexity for
a deterministic proof). Both noted in `docs/LEARNINGS.md`.

## Batch 3 — ai (deterministic, in-process) ✅ complete
Source: research T3 (fuzzing/AI). Built CI-safe: no live LLM, no API key — an LLM judge
is stood in for deterministically so the lane is hermetic and reproducible.

| Candidate | Dep | Failure class | Status |
|-----------|-----|---------------|--------|
| `agentic_pbt` | hypothesis | agent-inferred property violated (idempotence) — Anthropic PBT pattern | ✅ shipped |
| `llm_eval` | deepeval | LLM hallucination — claim ungrounded in context | ✅ shipped |

Deviation: both run deterministically without a live model (the agent's property
inference is encoded; the LLM judge is a deterministic metric), so the `ai` lane needs
no secret and runs on the fast (non-Docker) lane. Noted in `docs/LEARNINGS.md`.

## Batch 4 — lib + integration (security-leaning)
Source: extends Batches 1-3 toward auth / crypto / supply-chain failure classes.

**lib (4) — shipped** (branch `feat/batch4-lib-security`):

| Candidate | Dep | Failure class | Status |
|-----------|-----|---------------|--------|
| crypto_correctness | cryptography | unauthenticated encryption accepts a tampered ciphertext (CWE-327/353) | ✅ shipped |
| secret_scanning | detect-secrets | naive `password=` grep misses real secrets (CWE-798) | ✅ shipped |
| sql_orm | sqlalchemy | ORM model dropped a UNIQUE constraint a mock can't enforce | ✅ shipped |
| retry_resilience | tenacity | policy retries a permanent (non-retryable) error (CWE-754) | ✅ shipped |

**integration (4) — shipped** (testcontainers, needs Docker):

| Candidate | Dep | Failure class | Status |
|-----------|-----|---------------|--------|
| vault_secrets | hvac | over-broad secret read — parent path vs single key (CWE-200) | ✅ shipped |
| elasticsearch_index | elasticsearch | missing-refresh read-after-write inconsistency | ✅ shipped |
| rabbitmq_redelivery | pika | auto-ack loses a message on processing failure (CWE-754) | ✅ shipped |
| keycloak_oidc | pyjwt | forged token accepted without signature verification (CWE-347) | ✅ shipped |

## Batch 5 — ai ✅ complete
Source: research T7 ("AI Workflows, Cross-Talk, Tools, Errors"). Frameworks verified
real (DeepEval/G-Eval, the MetaQA metamorphic pattern); the doc's comparison tables /
exact percentages are unsourced and were ignored. Lane stays CI-safe: deterministic
metric or local stand-in, no live LLM / no API key.

| Candidate | Dep | Failure class | Status |
|-----------|-----|---------------|--------|
| `rag_faithfulness` | deepeval | low context **precision** — retriever returns off-topic distractors (the retrieval half `llm_eval` doesn't cover) | ✅ shipped |
| `geval_rubric` | deepeval | output violates a hard-coded rubric step (deterministic G-Eval stand-in) | ✅ shipped |
| `metamorphic_stability` | hypothesis | output swings under semantically-neutral perturbations (MetaQA relation) | ✅ shipped |

Deviation: `rag_faithfulness` uses **deepeval context-precision**, not Ragas — Ragas is
stale (0.4.3, Jan 2026) and `llm_eval` already covers generation faithfulness, so the
distinct, useful angle is retrieval precision. `geval_rubric` uses a deterministic
`RubricMetric` rather than live G-Eval (which needs an LLM judge), per the no-live-LLM
invariant. No new dependency — both deepeval and hypothesis were already in the `ai` extra.

## Batch 6 — lib (auth / authorization) ✅ complete
Source: the 2026-06-15 idea backlog (`project_dep_test_kit_retro.md` named gaps — RBAC scopes
and JWT alg-confusion, with the `pyjwt>=2.13` floor unproven by any harness). Both are
in-process lib harnesses (no Docker), so they run on the fast lane + self-test glob.

| Candidate | Dep | Failure class | Status |
|-----------|-----|---------------|--------|
| `jwt_alg_confusion` | pyjwt[crypto] | RS256→HS256 public-key confusion + `alg=none` accepted by a verifier that trusts the token's `alg` (CWE-347 / CVE-2026-48526); proves the `>=2.13` floor | ✅ shipped |
| `rbac_authz_differential` | hypothesis | authorizer drops the action half of (resource, action) → read→write escalation; caught by a Cedar/Lean-style differential vs a reference model | ✅ shipped |

Note: `jwt_alg_confusion` adds `pyjwt[crypto]>=2.13` to the **`lib`** extra (it was
integration-only for `keycloak_oidc`); both harnesses import their dep directly, so no deptry
ignore is needed.

Out of scope for this harness library (platform/agent work, not testing harnesses):
agent protocols (MCP/A2A/ACP/SDE), orchestration stacks (LangGraph/CrewAI/AutoGen),
and tracing (Arize Phoenix / OpenTelemetry — the `log.sh` JSONL is the lightweight
stand-in already in `.claude/hooks/`).

## Batch 7 — ai (judge reliability) ✅ complete
Source: the 2026-06-15 idea backlog (`project_dep_test_kit_retro.md` flagged the 3 prior ai
harnesses as circular / stable-by-construction). This one tests the *judge itself*, fusing two
pillars no mainstream eval tool packages together. Deterministic, no live LLM / no API key.

| Candidate | Dep | Failure class | Status |
|-----------|-----|---------------|--------|
| `judge_reliability` | deepeval | an LLM-judge that is non-deterministic across identical runs (variance) OR content-blind (cites no verbatim span) — both invisible to a structural/G-Eval check | ✅ shipped |

Note: no new dependency (deepeval already in the `ai` extra). Both pillars are machine-checkable
with no second LLM — verdict dispersion across N runs, and a normalized verbatim-substring span
predicate with a minimum length so a trivial token cannot satisfy it. Complements (does not
replace) `geval_rubric`; hardening `geval_rubric`/`metamorphic_stability` is a noted follow-on.

## Batch 8 — lib (dependency surface) ✅ complete
Source: the 2026-06-15 idea backlog. LLM codegen invents attributes on real packages (the
Llama `AttributeError` pattern); static type-checkers go blind on untyped/C-extension/dynamic
surfaces. Anchored on a real dependency (NOT pure stdlib — that would belong in `testing-kits`).

| Candidate | Dep | Failure class | Status |
|-----------|-----|---------------|--------|
| `hallucinated_symbol` | pydantic | a hallucinated `pkg.<attr>` that does not exist on the live, version-pinned package surface, missed by a naive "does the module import?" check | ✅ shipped |

Note: introspects the live installed pydantic surface (`hasattr` honors PEP 562 `__getattr__` +
C-extension members; `__all__` for re-exports), pinned to `importlib.metadata.version`. No new
dependency (pydantic already in the `lib` extra). Scope is single-level `pydantic.<attr>`;
multi-level chains and a general any-package resolver are a noted follow-on.

## Batch 9 — lib (dependency surface + LLM-app hygiene) ✅ complete
Source: the 2026-06-15 Gemini docs ("AI Development Methodologies 2026" + "AI and BDD in 2026").
Both deterministic, in-process, dependency-backed. The docs' *failure classes* were the useful
signal; their market/percentage statistics were treated as unverified and ignored.

| Candidate | Dep | Failure class | Status |
|-----------|-----|---------------|--------|
| `hallucinated_dependency` | packaging | a pinned `name==version` that was never published (hallucinated version of a real package, or a typosquat), missed by a naive "is the name installed?" check — the Sonatype AI-supply-chain class, version-level sibling of `hallucinated_symbol` | ✅ shipped |
| `prompt_cache_prefix` | pydantic | volatile content (timestamp / request-id / uuid) baked into the cached prompt prefix busts the cache every call, missed by a naive "a `cache_control` breakpoint exists" check | ✅ shipped |

Note: `hallucinated_dependency` adds `packaging` to the `lib` extra (PEP 440 parsing; was
transitive, now direct) and resolves pins against the LIVE installed environment, so real pins are
built from live versions and survive `uv.lock` bumps. `prompt_cache_prefix` adds no dependency
(pydantic models/validates the content-block + `cache_control` contract) — a pure-stdlib string
scanner would belong in `testing-kits`. Out of scope from these docs (platform/agent work, not
harnesses): SDD frameworks (CURRANTE / Spec-Kit / OpenSpec), MemCoder / Codified Context / Active
Context Compression, OpenDev, SWE-CI, and the agentic test-automation vendor matrix.

## Backlog — next candidates (not yet built)
Captured 2026-06-16. Each still needs a planted-bug proof and (for lib/ai) a `VACUITY_TARGETS`.

**Harness candidates**
| Candidate | Flavor / Dep | Failure class |
|-----------|--------------|---------------|
| `mcp_schema_confusion` | lib / pydantic | a non-additive MCP tool-schema change (removed field / narrowed type / new required input) breaks clients, missed by a naive "still valid JSON Schema" check |
| `doc_freshness` | lib / packaging or pydantic | a docstring/README claim about a symbol or version has drifted from the live code, missed by a check that never resolves the claim (the "freshness score" class) |
| concurrency / idempotency | integration | a non-idempotent handler double-applies under at-least-once redelivery; a race a single-threaded mock can't surface (retro gap) |
| txn-isolation | integration / psycopg | a read-committed assumption breaks under a concurrent writer (lost update / phantom) — needs two real connections |

Note: `gherkin_declarative` (imperative-vs-declarative Gherkin) is a **pure-stdlib text check** → it
belongs in `testing-kits`, not here (no dependency anchor), unless built on a real Gherkin parser.

**Gate / tooling hardening (not harnesses)**
- Harden `tools/scan_staged.py` — it is itself vacuous-green: the regex misses `client_secret=` /
  `access_token=` shapes and has no entropy detector. Wire in `detect-secrets` (already a dep) so the
  repo's own secret gate has the coverage the `secret_scanning` harness proves a naive grep lacks.
- A real incremental per-harness **mutation** runner (the ADR-0006 deferred item the vacuity gate
  only partially covers), and distinguishing vacuity-gate "red via assertion" from "red via crash".

## Notes
- **Batch naming:** a batch number is assigned when its harnesses ship and is never reused or
  retroactively reassigned. A harness added on its own (outside a planned batch) is labeled
  **Standalone** (e.g. `network_chaos`), not folded into a batch number after the fact — this
  avoids the "Batch 4 means two different things" overload seen earlier.
- Integration harnesses run as a separate CI job (Docker); they stay off the fast lib lane.
- The `ai` lane is in-process and deterministic; it runs alongside `lib` (no Docker, no key).
- Coverage-guided fuzzing (Atheris) and the research-frontier fuzzers in T3 are systems-
  level (C/kernel/JIT) and out of scope for this Python harness library.
