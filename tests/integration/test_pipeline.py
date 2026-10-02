import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import requests
from sqlalchemy import create_engine, text
from werkzeug.serving import make_server

from quakewatch.app import create_app
from quakewatch.db import database_url, migrate
from quakewatch.messaging import DatabaseQueue, RabbitQueue
from quakewatch.worker import Worker
from tests.fixtures import FEED


class FeedHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(FEED).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def serve_in_background(server):
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture
def engine(tmp_path):
    url = os.environ.get("DATABASE_URL") and database_url() or f"sqlite:///{tmp_path}/integration.db"
    engine = create_engine(url)
    migrate(engine)
    with engine.begin() as conn:
        for table in ("earthquakes", "region_stats", "messages"):
            conn.execute(text(f"DELETE FROM {table}"))
    return engine


@pytest.fixture
def queue(engine):
    rabbit_url = os.environ.get("RABBIT_URL")
    if not rabbit_url:
        return DatabaseQueue(engine)
    queue = RabbitQueue(rabbit_url, name="integration-test-collected")
    queue.consume_available(lambda body: None)
    return queue


def test_collect_analyze_and_serve(engine, queue):
    feed = serve_in_background(HTTPServer(("127.0.0.1", 0), FeedHandler))
    web = serve_in_background(make_server("127.0.0.1", 0, create_app(engine, run_worker=False)))
    web_url = f"http://127.0.0.1:{web.server_port}"

    try:
        Worker(engine, queue, collect_every_seconds=60, feed_url=f"http://127.0.0.1:{feed.server_port}/feed").run_once(now=0)

        search = requests.get(f"{web_url}/?q=alaska", timeout=5)
        assert "You searched for: <strong>alaska</strong>" in search.text
        assert "Beluga, Alaska" in search.text

        regions = requests.get(f"{web_url}/api/stats", timeout=5).json()["regions"]
        assert [(r["region"], r["quake_count"]) for r in regions] == [("Alaska", 2), ("Japan", 1)]

        metrics = requests.get(f"{web_url}/metrics", timeout=5).text
        assert "quakewatch_analyzer_runs_total" in metrics
    finally:
        feed.shutdown()
        web.shutdown()
