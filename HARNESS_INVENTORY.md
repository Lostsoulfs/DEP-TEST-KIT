# Harness Inventory

**Total: 12 harnesses** (6 lib, 6 integration). This repo grows in batches of ≤6;
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

### mutation_quality — mutmut vacuous-green detector
- **File:** `harnesses/lib/mutation_quality_test_harness.py`
- **Tests:** `tests/lib/test_mutation_quality_test_harness.py` (+ `_proof.py`)
- **Dep:** `mutmut` (invoked as a CLI runner via subprocess, not imported)
- **Why:** line coverage proves a line *ran*, not that any test *asserts* it —
  "vacuous green", this repo's defining bug class. mutmut injects faults (`>`→`>=`,
  `0`→`1`) and a surviving mutant is a line the suite runs but does not pin.
- **How:** runs mutmut in an isolated temp project (never the repo) on a one-line
  target against a STRONG suite (kills all) and a WEAK suite (vacuous); counts
  survivors from `mutmut results`.
- **Proof:** the weak suite leaves mutants alive (survivors > 0); the strong suite
  leaves none. The weak>0 check also guarantees mutmut actually bit.

### openapi_fuzz — schemathesis contract-drift fuzzer
- **File:** `harnesses/lib/openapi_fuzz_test_harness.py`
- **Tests:** `tests/lib/test_openapi_fuzz_test_harness.py` (+ `_proof.py`)
- **Deps:** `schemathesis`, `flask`
- **Why:** handwritten API tests miss *drift* from the OpenAPI contract — a field
  returned with the wrong type, an undeclared shape, a 500 on an untried input.
  schemathesis generates requests from the schema and validates every response, so
  the schema becomes an executable spec.
- **How:** two Flask (WSGI) apps serve a schema declaring `GET /widget` →
  `{count: integer}`; the oracle returns an int, the buggy app a string. Runs fully
  in-process (WSGI, no network); `call_and_validate` raises on drift.
- **Proof:** the string-typed `count` is caught (`FailureGroup`); the conformant
  app validates clean.

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

### redis_cache — real TTL on ephemeral Redis
- **File:** `harnesses/integration/redis_cache_test_harness.py`
- **Dep:** `redis` · **Isolation:** logical DB index per xdist worker
- **Why:** a mock has no TTL; a cache that writes a plain SET (no expiry) passes every
  mock test and leaks stale data forever.
- **Proof:** the buggy cache's key reports `TTL == -1` (no expiry) against real Redis;
  the correct one reports a positive TTL.

### mysql_store — real utf8mb3/utf8mb4 charset width on ephemeral MySQL
- **File:** `harnesses/integration/mysql_store_test_harness.py`
- **Dep:** `pymysql` · **Isolation:** DROP+CREATE per test (MySQL DDL auto-commits)
- **Why:** `utf8`/`utf8mb3` can't hold 4-byte characters; only a real MySQL enforces it.
- **Proof:** the buggy (utf8mb3) store raises a MySQL error on a 4-byte char; the
  correct (utf8mb4) store round-trips it.

### mongo_store — real unique index on ephemeral MongoDB
- **File:** `harnesses/integration/mongo_store_test_harness.py`
- **Dep:** `pymongo` · **Isolation:** logical database per xdist worker
- **Why:** Mongo stores duplicates unless a unique index exists; a mock can't enforce one.
- **Proof:** the buggy store (no index) ends with two documents; the correct store
  raises `DuplicateKeyError`.

### object_store — real S3 byte round-trip on ephemeral MinIO
- **File:** `harnesses/integration/object_store_test_harness.py`
- **Deps:** `boto3`, `minio` · **Isolation:** unique bucket per test
- **Why:** a mock hands your `str` back; only a real round-trip exposes corrupt bytes.
- **Proof:** the buggy store writes Latin-1 bytes that raise `UnicodeDecodeError` when
  read back under the UTF-8 contract; the correct store round-trips the text.

### kafka_stream — real consumer offset-reset on ephemeral Kafka (KRaft)
- **File:** `harnesses/integration/kafka_stream_test_harness.py`
- **Dep:** `confluent-kafka` · **Isolation:** unique topic + consumer group per test
- **Why:** `auto.offset.reset=latest` silently drops messages produced before the
  consumer joined — a data-loss bug a mock broker can't model.
- **Proof:** the buggy (`latest`) reader receives nothing for a pre-existing message;
  the correct (`earliest`) reader replays it.

## Convention
See `template/harness_template.py` for the shape and `docs/decisions/0001-stack-decisions.md`
for why each dependency/tool was chosen.
