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

Out of scope for this harness library (platform/agent work, not testing harnesses):
agent protocols (MCP/A2A/ACP/SDE), orchestration stacks (LangGraph/CrewAI/AutoGen),
and tracing (Arize Phoenix / OpenTelemetry — the `log.sh` JSONL is the lightweight
stand-in already in `.claude/hooks/`).

## Notes
- Integration harnesses run as a separate CI job (Docker); they stay off the fast lib lane.
- The `ai` lane is in-process and deterministic; it runs alongside `lib` (no Docker, no key).
- Coverage-guided fuzzing (Atheris) and the research-frontier fuzzers in T3 are systems-
  level (C/kernel/JIT) and out of scope for this Python harness library.
