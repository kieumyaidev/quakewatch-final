import json
import logging
from datetime import datetime, timezone

from sqlalchemy import Engine, text

from quakewatch.metrics import analyzer_runs

logger = logging.getLogger(__name__)


def analyze(engine: Engine) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT region, COUNT(*) AS quake_count, MAX(magnitude) AS max_magnitude, "
            "AVG(magnitude) AS avg_magnitude, MAX(occurred_at) AS last_occurred_at "
            "FROM earthquakes GROUP BY region"
        )).all()
        conn.execute(text("DELETE FROM region_stats"))
        for row in rows:
            conn.execute(text(
                "INSERT INTO region_stats (region, quake_count, max_magnitude, avg_magnitude, last_occurred_at, analyzed_at) "
                "VALUES (:region, :quake_count, :max_magnitude, :avg_magnitude, :last_occurred_at, :analyzed_at)"
            ), {**row._mapping, "analyzed_at": now})
    analyzer_runs.inc()
    logger.info("analyzed %d regions", len(rows))
    return len(rows)


def handle_collected_event(engine: Engine, body: str) -> None:
    event = json.loads(body)
    logger.info("received collected event with %d new earthquakes", event["new_rows"])
    analyze(engine)


def region_stats(engine: Engine, limit: int = 20) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT region, quake_count, max_magnitude, avg_magnitude, last_occurred_at FROM region_stats "
            "ORDER BY quake_count DESC, region LIMIT :limit"
        ), {"limit": limit})
        return [dict(row._mapping) for row in rows]
