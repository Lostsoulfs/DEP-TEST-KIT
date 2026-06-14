"""Fixtures for the integration lane (research T2 pattern).

Each service runs as one session-scoped ephemeral container (testcontainers, ryuk
cleanup, dynamic ports). Isolation is per service:
- PostgreSQL: autocommit=False connection + teardown ROLLBACK (DDL is transactional).
- Redis: a logical DB index per pytest-xdist worker.
- MySQL: DROP+CREATE per test (MySQL DDL auto-commits, so rollback can't undo it).
- MongoDB: a logical database per worker; the collection is dropped around each test.
- MinIO (S3): a unique bucket per test, emptied and deleted on teardown.
- Kafka (KRaft): a fresh topic + consumer group per test (the test supplies them).
"""

from __future__ import annotations

import uuid

import pytest


# --- PostgreSQL ----------------------------------------------------------------
@pytest.fixture(scope="session")
def postgres_container():
    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer("postgres:16-alpine").with_command(
        "-c fsync=off -c synchronous_commit=off -c full_page_writes=off"
    )
    with container as pg:
        yield pg


@pytest.fixture()
def pg_conn(postgres_container):
    import psycopg

    conn = psycopg.connect(postgres_container.get_connection_url(driver=None), autocommit=False)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


# --- Redis ---------------------------------------------------------------------
def _worker_db(worker_id: str) -> int:
    # Map each xdist worker to a distinct Redis DB index so parallel workers never
    # collide on keys or FLUSHDB. "master" (no xdist) -> 0.
    if worker_id == "master":
        return 0
    return (int(worker_id.replace("gw", "")) % 15) + 1


@pytest.fixture(scope="session")
def redis_container():
    from testcontainers.redis import RedisContainer

    with RedisContainer("redis:7-alpine") as r:
        yield r


@pytest.fixture()
def redis_client(redis_container, worker_id):
    import redis

    client = redis.Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        db=_worker_db(worker_id),
        decode_responses=True,
    )
    client.flushdb()
    try:
        yield client
    finally:
        client.flushdb()
        client.close()


# --- MySQL ---------------------------------------------------------------------
@pytest.fixture(scope="session")
def mysql_container():
    from testcontainers.mysql import MySqlContainer

    with MySqlContainer("mysql:8.0") as m:
        yield m


@pytest.fixture()
def mysql_conn(mysql_container):
    from urllib.parse import urlparse

    import pymysql

    u = urlparse(mysql_container.get_connection_url())  # mysql+pymysql://user:pass@host:port/db
    conn = pymysql.connect(
        host=u.hostname,
        port=u.port,
        user=u.username,
        password=u.password,
        database=u.path.lstrip("/"),
    )
    try:
        yield conn
    finally:
        conn.close()


# --- MongoDB -------------------------------------------------------------------
@pytest.fixture(scope="session")
def mongo_container():
    from testcontainers.mongodb import MongoDbContainer

    with MongoDbContainer("mongo:7.0") as m:
        yield m


@pytest.fixture()
def mongo_db(mongo_container, worker_id):
    from pymongo import MongoClient

    client = MongoClient(mongo_container.get_connection_url())
    name = f"test_{worker_id}"
    db = client[name]
    db.drop_collection("users")
    try:
        yield db
    finally:
        client.drop_database(name)
        client.close()


# --- MinIO (S3) ----------------------------------------------------------------
@pytest.fixture(scope="session")
def minio_container():
    from testcontainers.minio import MinioContainer

    with MinioContainer() as m:
        yield m


@pytest.fixture()
def s3_client(minio_container):
    import boto3

    cfg = minio_container.get_config()  # {"endpoint": "host:port", "access_key", "secret_key"}
    return boto3.client(
        "s3",
        endpoint_url=f"http://{cfg['endpoint']}",
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
        region_name="us-east-1",
    )


@pytest.fixture()
def s3_bucket(s3_client):
    name = f"test-{uuid.uuid4().hex[:12]}"
    s3_client.create_bucket(Bucket=name)
    try:
        yield name
    finally:
        contents = s3_client.list_objects_v2(Bucket=name).get("Contents", [])
        for obj in contents:
            s3_client.delete_object(Bucket=name, Key=obj["Key"])
        s3_client.delete_bucket(Bucket=name)


# --- Kafka (KRaft) -------------------------------------------------------------
@pytest.fixture(scope="session")
def kafka_bootstrap():
    from testcontainers.kafka import KafkaContainer

    with KafkaContainer("confluentinc/cp-kafka:7.6.0").with_kraft() as k:
        yield k.get_bootstrap_server()


# --- Toxiproxy network chaos ---------------------------------------------------
# Redis reached THROUGH a Toxiproxy proxy on a shared Docker network, so a test can
# inject network faults (a stall) and prove the client's timeout handling. Both
# containers join one Network; the proxy forwards to `redis-upstream:6379`.
@pytest.fixture(scope="session")
def _chaos_stack():
    import time
    import urllib.error
    import urllib.request

    from testcontainers.core.container import DockerContainer
    from testcontainers.core.network import Network
    from testcontainers.redis import RedisContainer

    net = Network()
    net.create()
    try:
        redis_up = (
            RedisContainer("redis:7-alpine")
            .with_network(net)
            .with_network_aliases("redis-upstream")
        )
        toxi = (
            DockerContainer("ghcr.io/shopify/toxiproxy:2.12.0")
            .with_network(net)
            .with_exposed_ports(8474, 16379)
        )
        with redis_up, toxi:
            host = toxi.get_container_host_ip()
            api_port = int(toxi.get_exposed_port(8474))
            # Readiness: poll the Toxiproxy control API rather than guess a log line.
            version_url = f"http://{host}:{api_port}/version"
            for _ in range(50):
                try:
                    urllib.request.urlopen(version_url, timeout=1)
                    break
                except urllib.error.URLError:
                    time.sleep(0.2)
            yield {
                "host": host,
                "api_port": api_port,
                "proxy_port": int(toxi.get_exposed_port(16379)),
            }
    finally:
        net.remove()


@pytest.fixture()
def chaos_proxy(_chaos_stack):
    from toxiproxy import Toxiproxy

    server = Toxiproxy()
    server.update_api_consumer(_chaos_stack["host"], _chaos_stack["api_port"])
    proxy = server.create(
        name="redis-chaos",
        listen="0.0.0.0:16379",
        upstream="redis-upstream:6379",
    )
    try:
        yield proxy, _chaos_stack
    finally:
        proxy.destroy()


@pytest.fixture()
def redis_via_proxy(chaos_proxy):
    """Factory: socket_timeout -> redis.Redis connected through Toxiproxy."""
    import redis

    _proxy, stack = chaos_proxy

    def factory(socket_timeout):
        return redis.Redis(
            host=stack["host"],
            port=stack["proxy_port"],
            socket_timeout=socket_timeout,
            socket_connect_timeout=2,
            decode_responses=True,
        )

    return factory


# --- Vault (KV-v2, dev mode) ---------------------------------------------------
_VAULT_TOKEN = "dev-root"  # dev-mode root token; container-local, never a real secret


@pytest.fixture(scope="session")
def vault_container():
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.waiting_utils import wait_for_logs

    container = (
        DockerContainer("hashicorp/vault:1.17")
        .with_env("VAULT_DEV_ROOT_TOKEN_ID", _VAULT_TOKEN)
        .with_env("VAULT_DEV_LISTEN_ADDRESS", "0.0.0.0:8200")
        .with_exposed_ports(8200)
    )
    with container as vault:
        wait_for_logs(vault, "Vault server started")
        yield vault


@pytest.fixture()
def vault_client(vault_container):
    import hvac

    host = vault_container.get_container_host_ip()
    port = vault_container.get_exposed_port(8200)
    client = hvac.Client(url=f"http://{host}:{port}", token=_VAULT_TOKEN)
    # Seed one KV-v2 secret with several sibling keys; only `password` is "requested".
    client.secrets.kv.v2.create_or_update_secret(
        path="app/db",
        secret={"password": "p@ss", "username": "dbuser", "api_key": "AKIAEXAMPLE"},
    )
    return client


# --- Elasticsearch -------------------------------------------------------------
@pytest.fixture(scope="session")
def es_container():
    from testcontainers.elasticsearch import ElasticSearchContainer

    with ElasticSearchContainer("docker.elastic.co/elasticsearch/elasticsearch:8.13.4") as es:
        yield es


@pytest.fixture()
def es_client(es_container):
    from elasticsearch import Elasticsearch

    # This testcontainers version dropped ElasticSearchContainer.get_url(); build it from
    # host+port. The 8.x image runs with xpack.security disabled (plain http, no auth).
    url = f"http://{es_container.get_container_host_ip()}:{es_container.get_exposed_port(es_container.port)}"
    client = Elasticsearch(url)
    if client.indices.exists(index="docs"):
        client.indices.delete(index="docs")
    client.indices.create(index="docs")
    try:
        yield client
    finally:
        if client.indices.exists(index="docs"):
            client.indices.delete(index="docs")
        client.close()


# --- RabbitMQ ------------------------------------------------------------------
@pytest.fixture(scope="session")
def rabbitmq_container():
    from testcontainers.rabbitmq import RabbitMqContainer

    with RabbitMqContainer("rabbitmq:3.13-management") as rmq:
        yield rmq


@pytest.fixture()
def rabbit_channel(rabbitmq_container):
    """Yields (channel, queue): a fresh pika channel + a unique per-test queue name."""
    import pika

    params = rabbitmq_container.get_connection_params()
    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    queue = f"jobs_{uuid.uuid4().hex[:8]}"
    channel.queue_declare(queue=queue, durable=False)
    try:
        yield channel, queue
    finally:
        try:
            channel.queue_delete(queue)
        finally:
            conn.close()


# --- Keycloak (real OIDC; valid + forged tokens) -------------------------------
@pytest.fixture(scope="session")
def keycloak_oidc():
    """Start Keycloak, create a realm/client/user, mint a real RS256 token, and
    craft a forged token signed with a throwaway key (kid absent from JWKS).

    Returns: {jwks_url, issuer, audience, valid_token, forged_token}.
    """
    import time

    import jwt
    import requests
    from cryptography.hazmat.primitives.asymmetric import rsa
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.waiting_utils import wait_for_logs

    realm, client_id, audience = "demo", "demo-client", "demo-client"
    user, password = "alice", "alice-pw"
    container = (
        DockerContainer("quay.io/keycloak/keycloak:25.0")
        .with_env("KEYCLOAK_ADMIN", "admin")
        .with_env("KEYCLOAK_ADMIN_PASSWORD", "admin")
        .with_command("start-dev")
        .with_exposed_ports(8080)
    )
    with container as kc:
        wait_for_logs(kc, "Running the server", timeout=120)
        base = f"http://{kc.get_container_host_ip()}:{kc.get_exposed_port(8080)}"

        admin_tok = requests.post(
            f"{base}/realms/master/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli",
                  "username": "admin", "password": "admin"},
            timeout=30,
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {admin_tok}"}
        for url, body in [
            (f"{base}/admin/realms", {"realm": realm, "enabled": True}),
            (f"{base}/admin/realms/{realm}/clients", {
                "clientId": client_id, "publicClient": True,
                "directAccessGrantsEnabled": True, "redirectUris": ["*"],
                # Keycloak's access-token `aud` defaults to "account"; add an audience
                # mapper so `demo-client` is in `aud` and the oracle's audience check passes.
                "protocolMappers": [{
                    "name": "demo-audience",
                    "protocol": "openid-connect",
                    "protocolMapper": "oidc-audience-mapper",
                    "config": {
                        "included.client.audience": client_id,
                        "access.token.claim": "true",
                        "id.token.claim": "false",
                    },
                }]}),
            (f"{base}/admin/realms/{realm}/users", {
                "username": user, "enabled": True, "emailVerified": True,
                # KC 25's declarative user profile triggers a "Verify Profile" action when
                # email/firstName/lastName are missing -> "Account is not fully set up".
                "email": f"{user}@example.com", "firstName": "Alice", "lastName": "Test"}),
        ]:
            r = requests.post(url, json=body, headers=h, timeout=30)
            if r.status_code not in (201, 409):  # 201 created, 409 already exists
                raise RuntimeError(f"Keycloak provisioning POST {url} -> {r.status_code}: {r.text[:400]}")

        # A freshly admin-created user inherits the realm's default required actions, which
        # block the password grant ("Account is not fully set up") even with a non-temporary
        # password in the create body. Fetch the user and explicitly clear required actions,
        # then set the password via the dedicated reset-password endpoint.
        uid = requests.get(
            f"{base}/admin/realms/{realm}/users",
            params={"username": user, "exact": "true"}, headers=h, timeout=30,
        ).json()[0]["id"]
        requests.put(
            f"{base}/admin/realms/{realm}/users/{uid}", headers=h, timeout=30,
            json={"requiredActions": [], "emailVerified": True, "enabled": True},
        )
        requests.put(
            f"{base}/admin/realms/{realm}/users/{uid}/reset-password", headers=h, timeout=30,
            json={"type": "password", "value": password, "temporary": False},
        )

        issuer = f"{base}/realms/{realm}"
        jwks_url = f"{issuer}/protocol/openid-connect/certs"
        tok_resp = requests.post(
            f"{issuer}/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": client_id,
                  "username": user, "password": password},
            timeout=30,
        )
        body = tok_resp.json()
        if "access_token" not in body:
            raise RuntimeError(f"Keycloak token request -> {tok_resp.status_code}: {tok_resp.text[:400]}")
        valid_token = body["access_token"]

        # Forged: a token signed by a key Keycloak's JWKS does not contain.
        rogue = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        forged_token = jwt.encode(
            {"sub": "attacker", "aud": audience, "iss": issuer, "exp": int(time.time()) + 3600},
            rogue, algorithm="RS256", headers={"kid": "rogue-key"},
        )
        yield {"jwks_url": jwks_url, "issuer": issuer, "audience": audience,
               "valid_token": valid_token, "forged_token": forged_token}
