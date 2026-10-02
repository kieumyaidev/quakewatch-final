from quakewatch.messaging import DatabaseQueue


def test_database_queue_delivers_messages_in_order_once(engine):
    queue = DatabaseQueue(engine)
    queue.publish("first")
    queue.publish("second")
    received = []

    assert queue.consume_available(received.append) == 2
    assert queue.consume_available(received.append) == 0
    assert received == ["first", "second"]


def test_message_stays_in_queue_when_handler_fails(engine):
    queue = DatabaseQueue(engine)
    queue.publish("event")

    def failing_handler(body):
        raise RuntimeError("boom")

    try:
        queue.consume_available(failing_handler)
    except RuntimeError:
        pass

    received = []
    queue.consume_available(received.append)
    assert received == ["event"]


def test_queues_are_separate(engine):
    DatabaseQueue(engine, "a").publish("for a")
    received = []

    DatabaseQueue(engine, "b").consume_available(received.append)

    assert received == []
