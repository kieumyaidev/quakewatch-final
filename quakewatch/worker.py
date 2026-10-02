import logging
import os
import threading
import time

from sqlalchemy import Engine

from quakewatch.analyzer import handle_collected_event
from quakewatch.collector import FEED_URL, collect
from quakewatch.messaging import MessageQueue

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, engine: Engine, queue: MessageQueue, collect_every_seconds: int, feed_url: str = FEED_URL) -> None:
        self.engine = engine
        self.queue = queue
        self.collect_every_seconds = collect_every_seconds
        self.feed_url = feed_url
        self.last_collected_at: float | None = None

    def run_once(self, now: float) -> None:
        if self.last_collected_at is None or now - self.last_collected_at >= self.collect_every_seconds:
            try:
                collect(self.engine, self.queue.publish, self.feed_url)
                self.last_collected_at = now
            except Exception:
                logger.warning("will retry collection on the next tick")
        self.queue.consume_available(lambda body: handle_collected_event(self.engine, body))

    def run_forever(self, tick_seconds: int = 5) -> None:
        while True:
            try:
                self.run_once(time.time())
            except Exception:
                logger.exception("worker tick failed")
            time.sleep(tick_seconds)


def start_in_background(worker: Worker) -> threading.Thread:
    thread = threading.Thread(target=worker.run_forever, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    from quakewatch.db import build_engine, migrate
    from quakewatch.messaging import build_queue

    logging.basicConfig(level=logging.INFO)
    engine = build_engine()
    migrate(engine)
    Worker(engine, build_queue(engine), int(os.environ.get("COLLECT_EVERY_SECONDS", 900))).run_forever()
