#!/usr/bin/env python3
"""Kafka consumer offset-reset integration test harness (testcontainers).

WHY:   A consumer's `auto.offset.reset` decides what a brand-new consumer group reads:
       `earliest` replays the log from the start, `latest` skips everything produced
       before it joined. A service that uses `latest` silently drops every message that
       arrived while it was down — a data-loss bug a mock broker (which just replays a
       list) cannot model. Only a real broker, with real offsets, distinguishes them.

HOW:   `publish` produces one message to a fresh topic. `TopicReader` consumes with
       `auto.offset.reset=earliest`; `BuggyTopicReader` ships the SAME code with
       `latest`. The proof produces a message, THEN reads with a fresh consumer group:
       the correct reader receives it, the buggy reader (joining after the write)
       receives nothing.

WHERE: integration/ — needs a real ephemeral Kafka (KRaft mode) via Docker. Uses
       `confluent-kafka` (added to the `integration` extra). Isolation (research T2):
       one session-scoped broker; each test uses a unique topic + consumer group. The
       bootstrap address is injected by `tests/integration/conftest.py`.

Self-test:
  python harnesses/integration/kafka_stream_test_harness.py --self-test
  (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time


def publish(bootstrap: str, topic: str, value: str) -> None:
    """Produce one message and block until it is delivered (auto-creates the topic)."""
    from confluent_kafka import Producer

    producer = Producer({"bootstrap.servers": bootstrap})
    producer.produce(topic, value.encode("utf-8"))
    producer.flush(15)


class TopicReader:
    offset_reset = "earliest"

    def __init__(self, bootstrap: str) -> None:
        self.bootstrap = bootstrap

    def read_all(
        self, topic: str, group: str, timeout: float = 15.0, stop_after: int | None = 1
    ) -> list[str]:
        from confluent_kafka import Consumer

        consumer = Consumer(
            {
                "bootstrap.servers": self.bootstrap,
                "group.id": group,
                "auto.offset.reset": self.offset_reset,
                "enable.auto.commit": False,
            }
        )
        consumer.subscribe([topic])
        out: list[str] = []
        deadline = time.time() + timeout
        try:
            while time.time() < deadline:
                msg = consumer.poll(1.0)
                if msg is None or msg.error():
                    continue
                out.append(msg.value().decode("utf-8"))
                # Stop as soon as we have what we expect; the "expect empty" case
                # (stop_after unreachable) naturally runs to the timeout.
                if stop_after is not None and len(out) >= stop_after:
                    break
        finally:
            consumer.close()
        return out


class BuggyTopicReader(TopicReader):
    """Identical reader, but it starts at `latest` — it skips pre-existing messages."""

    offset_reset = "latest"


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. Run `pytest -m integration` "
        f"(needs Docker). docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kafka offset-reset integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
