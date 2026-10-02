from unittest.mock import Mock, patch

from quakewatch.worker import Worker


def test_collects_then_waits_for_interval(engine):
    queue = Mock()
    queue.consume_available.return_value = 0
    worker = Worker(engine, queue, collect_every_seconds=60)

    with patch("quakewatch.worker.collect") as collect:
        worker.run_once(now=0)
        worker.run_once(now=30)
        worker.run_once(now=61)

    assert collect.call_count == 2
    assert queue.consume_available.call_count == 3


def test_failed_collection_is_retried_next_tick(engine):
    queue = Mock()
    worker = Worker(engine, queue, collect_every_seconds=60)

    with patch("quakewatch.worker.collect", side_effect=[RuntimeError("feed down"), 1]) as collect:
        worker.run_once(now=0)
        worker.run_once(now=1005)

    assert collect.call_count == 2
