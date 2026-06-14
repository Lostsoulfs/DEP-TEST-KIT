import uuid

import pytest

from harnesses.integration import kafka_stream_test_harness as h

pytestmark = pytest.mark.integration


def test_earliest_reader_receives_message(kafka_bootstrap) -> None:
    topic = f"t-{uuid.uuid4().hex[:8]}"
    h.publish(kafka_bootstrap, topic, "hello")
    reader = h.TopicReader(kafka_bootstrap)
    msgs = reader.read_all(topic, group=f"g-{uuid.uuid4().hex[:8]}")
    assert "hello" in msgs
