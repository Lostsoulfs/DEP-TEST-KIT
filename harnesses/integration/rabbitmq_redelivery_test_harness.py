#!/usr/bin/env python3
"""RabbitMQ ack/redelivery integration test harness (testcontainers + pika).

WHY: A consumer that auto-acknowledges a message BEFORE processing it loses the
message if processing then fails — the broker has already discarded it. A mock
broker never models redelivery, so the bug is invisible in unit tests. A real
RabbitMQ redelivers an un-acked message and drops an auto-acked one — the
difference that matters for at-least-once delivery (CWE-754 mishandled failure).

HOW: `AckingConsumer.process_one` fetches with `auto_ack=False` and acks only
AFTER the processor succeeds (nack+requeue on failure). `BuggyConsumer` fetches
with `auto_ack=True`, so a processor that raises leaves the message already
gone. `remaining_after_failure` returns the queue depth after a failing
process; the proof shows oracle keeps the message (1) and buggy loses it (0).

WHERE: integration/ — needs a real ephemeral RabbitMQ (Docker). The `pika`
channel is injected by `tests/integration/conftest.py` (`rabbit_channel`);
adds `pika` to the integration extra.

Self-test:
    python harnesses/integration/rabbitmq_redelivery_test_harness.py --self-test
    (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from typing import Callable


class AckingConsumer:
    """ORACLE: ack only after the processor succeeds; nack+requeue on failure."""

    def __init__(self, channel) -> None:
        self.channel = channel        # pika BlockingChannel, injected

    def process_one(self, queue: str, processor: Callable[[bytes], None]) -> bool:
        method, _props, body = self.channel.basic_get(queue=queue, auto_ack=False)
        if method is None:
            return False
        try:
            processor(body)
        except Exception:
            self.channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            raise
        self.channel.basic_ack(delivery_tag=method.delivery_tag)
        return True


class BuggyConsumer(AckingConsumer):
    """BUGGY: auto-acks on delivery, so a failing processor loses the message."""

    def process_one(self, queue: str, processor: Callable[[bytes], None]) -> bool:
        method, _props, body = self.channel.basic_get(queue=queue, auto_ack=True)  # BUG
        if method is None:
            return False
        processor(body)   # already acked: if this raises, the message is gone
        return True


def message_count(channel, queue: str) -> int:
    return channel.queue_declare(queue=queue, passive=True).method.message_count


def remaining_after_failure(consumer: AckingConsumer, channel, queue: str, settle: float = 3.0) -> int:
    """Process one message with a processor that always raises, then report how many
    messages remain on the queue (redelivered vs lost). `basic_nack(requeue=True)` is
    processed asynchronously by the broker, so poll the ready-count briefly for it to
    settle before reporting — otherwise a read right after the nack races the requeue."""
    def boom(_body: bytes) -> None:
        raise RuntimeError("processing failed")

    try:
        consumer.process_one(queue, boom)
    except Exception:
        pass
    deadline = time.monotonic() + settle
    count = message_count(channel, queue)
    while count == 0 and time.monotonic() < deadline:
        channel.connection.sleep(0.05)  # pika-friendly sleep that pumps the I/O loop
        count = message_count(channel, queue)
    return count


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. "
        "Run `pytest -m integration` (needs Docker). "
        f"docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RabbitMQ ack/redelivery integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
