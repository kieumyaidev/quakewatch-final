import os
from datetime import datetime, timezone
from typing import Callable, Protocol

import pika
from sqlalchemy import Engine, text

COLLECTED_QUEUE = "earthquakes-collected"


class MessageQueue(Protocol):
    def publish(self, body: str) -> None: ...

    def consume_available(self, handler: Callable[[str], None]) -> int: ...


class DatabaseQueue:
    def __init__(self, engine: Engine, name: str = COLLECTED_QUEUE) -> None:
        self.engine = engine
        self.name = name

    def publish(self, body: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO messages (queue, body, created_at) VALUES (:q, :b, :t)"),
                         {"q": self.name, "b": body, "t": _now()})

    def consume_available(self, handler: Callable[[str], None]) -> int:
        handled = 0
        while True:
            with self.engine.begin() as conn:
                row = conn.execute(text(
                    "SELECT id, body FROM messages WHERE queue = :q AND processed_at IS NULL ORDER BY id LIMIT 1"
                ), {"q": self.name}).first()
                if row is None:
                    return handled
                handler(row.body)
                conn.execute(text("UPDATE messages SET processed_at = :t WHERE id = :id"), {"t": _now(), "id": row.id})
            handled += 1


class RabbitQueue:
    def __init__(self, url: str, name: str = COLLECTED_QUEUE) -> None:
        self.parameters = pika.URLParameters(url)
        self.name = name

    def publish(self, body: str) -> None:
        with pika.BlockingConnection(self.parameters) as connection:
            channel = connection.channel()
            channel.queue_declare(queue=self.name, durable=True)
            channel.basic_publish(exchange="", routing_key=self.name, body=body.encode(),
                                  properties=pika.BasicProperties(delivery_mode=2))

    def consume_available(self, handler: Callable[[str], None]) -> int:
        handled = 0
        with pika.BlockingConnection(self.parameters) as connection:
            channel = connection.channel()
            channel.queue_declare(queue=self.name, durable=True)
            while True:
                method, _, body = channel.basic_get(queue=self.name, auto_ack=False)
                if method is None:
                    return handled
                handler(body.decode())
                channel.basic_ack(method.delivery_tag)
                handled += 1


def build_queue(engine: Engine) -> MessageQueue:
    rabbit_url = os.environ.get("RABBIT_URL")
    return RabbitQueue(rabbit_url) if rabbit_url else DatabaseQueue(engine)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
