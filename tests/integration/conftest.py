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
