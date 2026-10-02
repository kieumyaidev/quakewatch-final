import json

import pytest
import responses
from sqlalchemy import text

from quakewatch.collector import FEED_URL, collect
from quakewatch.db import migrate
from tests.fixtures import FEED


@responses.activate
def test_collect_saves_earthquakes_with_region(engine):
    responses.get(FEED_URL, json=FEED)

    assert collect(engine, publish=lambda body: None) == 3

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, magnitude, region FROM earthquakes ORDER BY id")).all()
    assert [tuple(r) for r in rows] == [("ak001", 2.4, "Alaska"), ("ak002", 3.6, "Alaska"), ("jp001", 4.8, "Japan")]


@responses.activate
def test_collect_twice_does_not_duplicate(engine):
    responses.get(FEED_URL, json=FEED)

    collect(engine, publish=lambda body: None)
    assert collect(engine, publish=lambda body: None) == 0

    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM earthquakes")).scalar() == 3


@responses.activate
def test_collect_publishes_event(engine):
    responses.get(FEED_URL, json=FEED)
    published = []

    collect(engine, publish=published.append)

    assert [json.loads(b) for b in published] == [{"fetched": 3, "new_rows": 3}]


@responses.activate
def test_collect_does_not_publish_when_feed_fails(engine):
    responses.get(FEED_URL, status=503)
    published = []

    with pytest.raises(Exception):
        collect(engine, publish=published.append)

    assert published == []


def test_migrations_run_once(engine):
    assert migrate(engine) == []
