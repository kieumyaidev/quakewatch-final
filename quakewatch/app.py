import logging
import os
import time

from flask import Flask, g, jsonify, render_template, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import Engine, text

from quakewatch.analyzer import region_stats
from quakewatch.db import build_engine, migrate
from quakewatch.messaging import build_queue
from quakewatch.metrics import request_latency
from quakewatch.worker import Worker, start_in_background


def search_earthquakes(engine: Engine, query: str, limit: int = 50) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, magnitude, place, region, occurred_at, url FROM earthquakes "
            "WHERE LOWER(place) LIKE :q OR LOWER(region) LIKE :q ORDER BY occurred_at DESC LIMIT :limit"
        ), {"q": f"%{query.lower()}%", "limit": limit})
        return [dict(row._mapping) for row in rows]


def create_app(engine: Engine | None = None, run_worker: bool | None = None) -> Flask:
    logging.basicConfig(level=logging.INFO)
    app = Flask(__name__)
    engine = engine or build_engine()
    migrate(engine)

    if run_worker if run_worker is not None else os.environ.get("RUN_WORKER") == "true":
        start_in_background(Worker(engine, build_queue(engine), int(os.environ.get("COLLECT_EVERY_SECONDS", 900))))

    @app.before_request
    def start_timer():
        g.started_at = time.perf_counter()

    @app.after_request
    def record_latency(response):
        request_latency.labels(request.endpoint or "unknown").observe(time.perf_counter() - g.started_at)
        return response

    @app.get("/")
    def index():
        query = request.args.get("q", "").strip()
        results = search_earthquakes(engine, query) if query else []
        return render_template("index.html", query=query, results=results)

    @app.get("/stats")
    def stats():
        return render_template("stats.html", stats=region_stats(engine))

    @app.get("/api/earthquakes")
    def api_earthquakes():
        query = request.args.get("q", "").strip()
        return jsonify(earthquakes=search_earthquakes(engine, query))

    @app.get("/api/stats")
    def api_stats():
        return jsonify(regions=region_stats(engine))

    @app.get("/health")
    def health():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics():
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=int(os.environ.get("PORT", 5000)))
