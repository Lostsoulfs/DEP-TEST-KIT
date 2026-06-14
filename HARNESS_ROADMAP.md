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

## Later — ai
Source: research T3 (fuzzing/AI). `agentic_pbt` — LLM-authored Hypothesis properties
(Anthropic red-team pattern); `llm_eval` (deepeval) for hallucination/relevancy.

## Notes
- Integration harnesses run as a separate CI job (Docker); they stay off the fast lib lane.
- Coverage-guided fuzzing (Atheris) and the research-frontier fuzzers in T3 are systems-
  level (C/kernel/JIT) and out of scope for this Python harness library.
