import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import requests
from sqlalchemy import Engine, text

from quakewatch.metrics import collection_failures, earthquakes_collected, last_collection
from quakewatch.regions import region_from_place

logger = logging.getLogger(__name__)

FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


@dataclass
class Earthquake:
    id: str
    magnitude: float | None
    place: str | None
    occurred_at: datetime
    longitude: float
    latitude: float
    depth_km: float | None
    url: str | None


def fetch_earthquakes(url: str = FEED_URL) -> list[Earthquake]:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return [parse_feature(f) for f in response.json()["features"]]


def parse_feature(feature: dict) -> Earthquake:
    props = feature["properties"]
    longitude, latitude, depth = feature["geometry"]["coordinates"]
    return Earthquake(
        id=feature["id"],
        magnitude=props.get("mag"),
        place=props.get("place"),
        occurred_at=datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc).replace(tzinfo=None),
        longitude=longitude,
        latitude=latitude,
        depth_km=depth,
        url=props.get("url"),
    )


def save_earthquakes(engine: Engine, earthquakes: list[Earthquake]) -> int:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_rows = 0
    with engine.begin() as conn:
        for quake in earthquakes:
            values = {**quake.__dict__, "region": region_from_place(quake.place), "collected_at": now}
            exists = conn.execute(text("SELECT 1 FROM earthquakes WHERE id = :id"), {"id": quake.id}).first()
            if exists:
                conn.execute(text(
                    "UPDATE earthquakes SET magnitude = :magnitude, place = :place, region = :region, "
                    "occurred_at = :occurred_at, longitude = :longitude, latitude = :latitude, depth_km = :depth_km, "
                    "url = :url, collected_at = :collected_at WHERE id = :id"
                ), values)
            else:
                conn.execute(text(
                    "INSERT INTO earthquakes (id, magnitude, place, region, occurred_at, longitude, latitude, depth_km, url, collected_at) "
                    "VALUES (:id, :magnitude, :place, :region, :occurred_at, :longitude, :latitude, :depth_km, :url, :collected_at)"
                ), values)
                new_rows += 1
    return new_rows


def collect(engine: Engine, publish: Callable[[str], None], url: str = FEED_URL) -> int:
    try:
        earthquakes = fetch_earthquakes(url)
        new_rows = save_earthquakes(engine, earthquakes)
    except Exception:
        collection_failures.inc()
        logger.exception("collection failed")
        raise

    earthquakes_collected.inc(new_rows)
    last_collection.set(time.time())
    publish(json.dumps({"fetched": len(earthquakes), "new_rows": new_rows}))
    logger.info("fetched %d earthquakes, %d new", len(earthquakes), new_rows)
    return new_rows


if __name__ == "__main__":
    from quakewatch.db import build_engine, migrate
    from quakewatch.messaging import build_queue

    logging.basicConfig(level=logging.INFO)
    engine = build_engine()
    migrate(engine)
    collect(engine, build_queue(engine).publish)
