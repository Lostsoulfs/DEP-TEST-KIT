"""Proof: a real RabbitMQ redelivers an un-acked message and drops an auto-acked
one. After a failing processor, the oracle leaves the message on the queue (1);
the buggy auto-ack consumer has already lost it (0)."""

import pytest

from harnesses.integration import rabbitmq_redelivery_test_harness as h

pytestmark = pytest.mark.integration


def test_proof_buggy_loses_message(rabbit_channel) -> None:
    channel, queue = rabbit_channel
    channel.basic_publish(exchange="", routing_key=queue, body=b"job-1")
    buggy = h.BuggyConsumer(channel)
    assert h.remaining_after_failure(buggy, channel, queue) == 0


def test_proof_oracle_redelivers_message(rabbit_channel) -> None:
    channel, queue = rabbit_channel
    channel.basic_publish(exchange="", routing_key=queue, body=b"job-1")
    oracle = h.AckingConsumer(channel)
    assert h.remaining_after_failure(oracle, channel, queue) == 1
