import pytest

from harnesses.integration import rabbitmq_redelivery_test_harness as h

pytestmark = pytest.mark.integration


def test_oracle_acks_on_success(rabbit_channel) -> None:
    channel, queue = rabbit_channel
    channel.basic_publish(exchange="", routing_key=queue, body=b"job-1")
    seen = []
    ok = h.AckingConsumer(channel).process_one(queue, seen.append)
    assert ok is True
    assert seen == [b"job-1"]
    assert h.message_count(channel, queue) == 0
