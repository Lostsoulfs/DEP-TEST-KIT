# Harness Inventory

**Total: 26 harnesses** (10 lib, 11 integration, 5 ai). This repo grows in batches of ≤6;
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

### crypto_correctness — authenticated vs unauthenticated encryption (cryptography)
- **File:** `harnesses/lib/crypto_correctness_test_harness.py`
- **Tests:** `tests/lib/test_crypto_correctness_test_harness.py` (+ `_proof.py`)
- **Dep:** `cryptography`
- **Why:** an "encrypt→decrypt, assert equal" test passes for an unauthenticated cipher
  (AES-CTR) exactly as for an authenticated one (AES-GCM); the gap shows only when an
  attacker tampers with the ciphertext (CWE-327 / CWE-353).
- **Proof:** a flipped ciphertext byte is silently accepted by the buggy (AES-CTR) box and
  rejected with `InvalidTag` by the oracle (AES-GCM).

### secret_scanning — detector coverage vs naive grep (detect-secrets)
- **File:** `harnesses/lib/secret_scanning_test_harness.py`
- **Tests:** `tests/lib/test_secret_scanning_test_harness.py` (+ `_proof.py`)
- **Dep:** `detect-secrets`
- **Why:** an in-house `password=` substring check passes its own example test yet is blind
  to the secrets that actually leak — AWS keys, high-entropy tokens, private-key blocks
  (CWE-798 hard-coded credentials).
- **Proof:** detect-secrets finds the planted AWS key / entropy token / private key in a
  blob that contains no literal `password=`; the naive grep finds none.

### sql_orm — real ORM constraint vs mocked Session (SQLAlchemy)
- **File:** `harnesses/lib/sql_orm_test_harness.py`
- **Tests:** `tests/lib/test_sql_orm_test_harness.py` (+ `_proof.py`)
- **Dep:** `sqlalchemy` (in-memory SQLite, in-process)
- **Why:** a mocked Session has no schema, so a model that forgot `unique=True` looks correct
  and still writes duplicates in production. A real engine — even `sqlite://` — raises
  `IntegrityError`. The in-process sibling of `postgres_store`, no Docker.
- **Proof:** the buggy model (`unique=False`) accepts a duplicate email against real SQLite;
  the oracle (`unique=True`) raises `IntegrityError`.

### retry_resilience — retry-only-transient vs retry-everything (tenacity)
- **File:** `harnesses/lib/retry_resilience_test_harness.py`
- **Tests:** `tests/lib/test_retry_resilience_test_harness.py` (+ `_proof.py`)
- **Dep:** `tenacity`
- **Why:** retry logic tested against a stub that eventually succeeds proves nothing about
  *which* errors it retries; a retry-on-`Exception` policy keeps hammering a permanent
  failure that can never succeed (CWE-754).
- **Proof:** the buggy policy attempts a permanent error `MAX_ATTEMPTS` times; the oracle
  (retry only `TransientError`) attempts it exactly once.

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

### network_chaos — missing socket timeout under a stalled upstream (Toxiproxy)
- **File:** `harnesses/integration/network_chaos_test_harness.py`
- **Deps:** `redis`, `toxiproxy-python` · **Isolation:** per-test Toxiproxy proxy on a shared
  Docker network
- **Why:** a Redis client with no `socket_timeout` blocks indefinitely when an upstream stalls
  (a hung node, a saturated proxy); an in-memory mock answers instantly and can't surface an
  unbounded hang.
- **Proof:** under a Toxiproxy `timeout` toxic, the resilient client (`socket_timeout=0.5`)
  raises `redis.TimeoutError` fast; the fragile client (no timeout) blocks the full stall and
  then raises `redis.ConnectionError` when the proxy drops the connection.

### vault_secrets — scoped vs over-broad KV-v2 read on ephemeral Vault
- **File:** `harnesses/integration/vault_secrets_test_harness.py`
- **Dep:** `hvac` · **Isolation:** one seeded KV-v2 secret per client fixture
- **Why:** a mocked secret client returns only what you stub; a real Vault reveals an over-broad
  read — returning every sibling key under a path instead of the one requested (CWE-200).
- **Proof:** the buggy reader returns the whole secret dict (all keys) against real Vault; the
  oracle returns just the requested value.

### elasticsearch_index — read-after-write consistency on ephemeral Elasticsearch
- **File:** `harnesses/integration/elasticsearch_index_test_harness.py`
- **Dep:** `elasticsearch` (8.x client + server) · **Isolation:** index recreated per test
- **Why:** Elasticsearch is near-real-time — a freshly indexed doc is not searchable until a
  refresh; a mock answers instantly and hides the inconsistency.
- **Proof:** the buggy store (no `refresh`) fails to find a just-indexed doc against real ES;
  the oracle (`refresh="wait_for"`) finds it.

### rabbitmq_redelivery — auto-ack message loss on ephemeral RabbitMQ
- **File:** `harnesses/integration/rabbitmq_redelivery_test_harness.py`
- **Dep:** `pika` · **Isolation:** a unique queue per test
- **Why:** auto-ack acknowledges a message before processing, so a processing failure loses it;
  a mock cannot model broker redelivery (CWE-754).
- **Proof:** under an always-failing processor, the buggy (auto-ack) consumer leaves 0 messages
  on the queue; the oracle (manual ack + nack/requeue) leaves it for redelivery (1).

### keycloak_oidc — real OIDC signature verification on ephemeral Keycloak
- **File:** `harnesses/integration/keycloak_oidc_test_harness.py`
- **Dep:** `pyjwt[crypto]` · **Isolation:** session realm/client/user + minted real + forged tokens
- **Why:** token validation is the most-mocked boundary; a verifier that skips the signature
  check accepts forged tokens while every mock-backed test still passes (CWE-347).
- **Proof:** against real Keycloak JWKS, the buggy verifier (`verify_signature=False`) accepts a
  token signed by a rogue key; the oracle rejects it and accepts only the genuine RS256 token.

## ai (deterministic, in-process — no live LLM, no API key)

### agentic_pbt — agent-inferred properties via Hypothesis
- **File:** `harnesses/ai/agentic_pbt_test_harness.py`
- **Dep:** `hypothesis`
- **Why:** the Anthropic "PBT with Claude" pattern infers properties from a function's
  name/contract and finds bugs no example was written for. Here the inferred properties
  (idempotence + a postcondition) are pinned and Hypothesis falsifies a violating impl.
- **Proof:** `buggy_ensure_prefix` (always prepends) satisfies the postcondition but
  breaks idempotence (`f(f("a")) == "ID_ID_a"`); the oracle holds.

### llm_eval — hallucination detection via deepeval
- **File:** `harnesses/ai/llm_eval_test_harness.py`
- **Dep:** `deepeval`
- **Why:** an LLM answer can't be checked with `==`; the failure class is the
  hallucination (a claim ungrounded in context). A deterministic deepeval `BaseMetric`
  scores faithfulness so the lane needs no API key.
- **Proof:** the "Eiffel Tower is in Berlin" answer scores 0.0 and is caught; the
  grounded answer scores 1.0 and passes. Deterministic metric stands in for the LLM
  judge (deviation noted in `docs/LEARNINGS.md`).

### rag_faithfulness — RAG context precision (deepeval)
- **File:** `harnesses/ai/rag_faithfulness_test_harness.py`
- **Dep:** `deepeval`
- **Why:** a RAG answer is only as good as its retrieval — a generator can be faithful to
  irrelevant context ("faithful to the wrong source"). `llm_eval` tests generation
  faithfulness; this tests the other half — retrieval **context precision**.
- **Proof:** a deterministic `ContextPrecisionMetric` (BaseMetric) scores the buggy
  retriever's off-topic distractors at 0.0 (caught); the oracle's on-topic chunk at 1.0.

### geval_rubric — deterministic rubric grader / G-Eval stand-in (deepeval)
- **File:** `harnesses/ai/geval_rubric_test_harness.py`
- **Dep:** `deepeval`
- **Why:** output must satisfy explicit rubric criteria (structure / required fields /
  value ranges / allowed enums); G-Eval scores these with an LLM judge — non-deterministic
  and key-dependent. A deterministic grader checks hard-coded `evaluation_steps` reproducibly.
- **Proof:** a `RubricMetric` (BaseMetric) runs each hard-coded step as a predicate; the
  buggy output (`confidence` 1.7, outside [0,1]) fails one step and is caught; the oracle
  passes all four.

### metamorphic_stability — output invariance under neutral perturbation (Hypothesis)
- **File:** `harnesses/ai/metamorphic_stability_test_harness.py`
- **Dep:** `hypothesis`
- **Why:** a grounded responder gives the same answer to semantically-equivalent phrasings;
  an ungrounded one swings under meaning-preserving perturbations (case / whitespace /
  punctuation). The MetaQA-style metamorphic relation `f(perturb(q)) == f(q)`, no model.
- **Proof:** Hypothesis composes neutral perturbations; the buggy (length-parity) responder
  flips its answer (caught on a trailing space); the normalized oracle is invariant.

## Convention
See `template/harness_template.py` for the shape and `docs/decisions/0001-stack-decisions.md`
for why each dependency/tool was chosen.
