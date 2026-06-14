# Harness Inventory

**Total: 5 harnesses** (4 lib, 1 integration). This repo grows in batches of ≤6;
see `HARNESS_ROADMAP.md` for what's next. Every harness ships a paired test and a
planted-bug **proof** test, and documents WHY / HOW / WHERE in its module docstring.

## lib (dependency-backed, in-process)

### property_roundtrip — Hypothesis round-trip property
- **File:** `harnesses/lib/property_roundtrip_test_harness.py`
- **Tests:** `tests/lib/test_property_roundtrip_test_harness.py` (+ `_proof.py`)
- **Dep:** `hypothesis`
- **Why:** example-based tests only check inputs a human imagined; a run-length
  encode→decode round-trip can pass on `"aaa"` yet fail on `"ab"`. Hypothesis
  generates thousands of inputs and **shrinks** a failure to the minimal case.
- **Proof:** a decoder that drops count-1 runs is falsified and shrunk to a 2-char
  counterexample; the oracle holds.

### schema_validation — polyfactory variant coverage (pydantic)
- **File:** `harnesses/lib/schema_validation_test_harness.py`
- **Tests:** `tests/lib/test_schema_validation_test_harness.py` (+ `_proof.py`)
- **Deps:** `pydantic`, `polyfactory`
- **Why:** a handler over a closed Enum/Union can silently omit a variant — the
  author who forgot the branch also forgot to test it. polyfactory's `coverage()`
  builds one instance per Enum value, exhausting the variant space no one
  enumerated by hand.
- **Proof:** the buggy `area` (missing the TRIANGLE branch) returns a degenerate
  `0.0` and is flagged across the coverage set; the oracle handles every variant.

### async_http_contract — respx transient-fault contract (httpx)
- **File:** `harnesses/lib/async_http_contract_test_harness.py`
- **Tests:** `tests/lib/test_async_http_contract_test_harness.py` (+ `_proof.py`)
- **Deps:** `respx`, `httpx`
- **Why:** a client tested only against a healthy 200 endpoint can have zero
  resilience; you can't provoke a real 503/timeout reliably in CI. respx injects
  the exact transient fault so the retry path is actually proven.
- **How:** async httpx clients driven via `asyncio.run` (no event-loop plugin);
  respx serves the fault on call 1 and a 200 on call 2.
- **Proof:** the no-retry client is caught on both a transient 503 and a read
  timeout; the retrying oracle recovers from each.

### temporal_logic — time-machine expiry boundary
- **File:** `harnesses/lib/temporal_logic_test_harness.py`
- **Tests:** `tests/lib/test_temporal_logic_test_harness.py` (+ `_proof.py`)
- **Dep:** `time-machine`
- **Why:** `<=` vs `<` in an expiry check is a one-char bug you can almost never
  observe with the wall clock (`now == expiry` exactly). time-machine pins the
  clock to the precise expiry instant, making it deterministic.
- **Proof:** the buggy `<=` check still reports a token valid at the exact expiry
  instant; the oracle expires it. The two agree everywhere except that instant.

## integration (real ephemeral service, needs Docker)

### postgres_store — real UNIQUE constraint on ephemeral PostgreSQL
- **File:** `harnesses/integration/postgres_store_test_harness.py`
- **Tests:** `tests/integration/test_postgres_store_test_harness.py` (+ `_proof.py`),
  fixtures in `tests/integration/conftest.py`
- **Deps:** `testcontainers`, `psycopg[binary]`
- **Why:** a mock cannot enforce a real schema. A store that "dedupes" via a UNIQUE
  constraint passes every mock test and still writes duplicates if the constraint
  was never declared. Only a real database reveals it.
- **How:** session-scoped container started with `fsync=off` (research T2 speed
  pattern); `autocommit=False` connection per test with a teardown ROLLBACK for
  pristine, near-zero-latency isolation.
- **Proof:** the buggy store (UNIQUE dropped from its DDL) writes a duplicate against
  real PostgreSQL (count == 2); the correct store raises `UniqueViolation`.

## Convention
See `template/harness_template.py` for the shape and `docs/decisions/0001-stack-decisions.md`
for why each dependency/tool was chosen.
