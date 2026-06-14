"""Proof: only a real broker distinguishes earliest from latest offset reset.

A message is produced first; then a brand-new consumer group reads. The buggy reader
(`auto.offset.reset=latest`) joins after the write and sees nothing — the data-loss
bug. The correct reader (`earliest`) replays it. A mock broker that just replays a list
cannot model offsets, so it would catch neither.
"""

import uuid

import pytest

from harnesses.integration import kafka_stream_test_harness as h

pytestmark = pytest.mark.integration


def test_proof_latest_reader_misses_prior_message(kafka_bootstrap) -> None:
    topic = f"t-{uuid.uuid4().hex[:8]}"
    h.publish(kafka_bootstrap, topic, "hello")
    reader = h.BuggyTopicReader(kafka_bootstrap)
    msgs = reader.read_all(topic, group=f"g-{uuid.uuid4().hex[:8]}")
    assert msgs == []  # latest skips what was produced before it joined


def test_proof_earliest_reader_receives_what_latest_misses(kafka_bootstrap) -> None:
    topic = f"t-{uuid.uuid4().hex[:8]}"
    h.publish(kafka_bootstrap, topic, "hello")
    reader = h.TopicReader(kafka_bootstrap)
    msgs = reader.read_all(topic, group=f"g-{uuid.uuid4().hex[:8]}")
    assert "hello" in msgs
