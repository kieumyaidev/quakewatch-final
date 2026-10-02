import json

import responses

from quakewatch.analyzer import analyze, handle_collected_event, region_stats
from quakewatch.collector import FEED_URL, collect
from tests.fixtures import FEED


@responses.activate
def test_analyze_groups_by_region(engine):
    responses.get(FEED_URL, json=FEED)
    collect(engine, publish=lambda body: None)

    assert analyze(engine) == 2

    stats = region_stats(engine)
    assert [(s["region"], s["quake_count"], s["max_magnitude"]) for s in stats] == [("Alaska", 2, 3.6), ("Japan", 1, 4.8)]
    assert stats[0]["avg_magnitude"] == 3.0


def test_analyze_with_no_data(engine):
    assert analyze(engine) == 0
    assert region_stats(engine) == []


@responses.activate
def test_handle_collected_event_runs_analysis(engine):
    responses.get(FEED_URL, json=FEED)
    collect(engine, publish=lambda body: None)

    handle_collected_event(engine, json.dumps({"fetched": 3, "new_rows": 3}))

    assert len(region_stats(engine)) == 2
