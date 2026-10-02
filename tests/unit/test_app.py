from datetime import datetime

import pytest

from quakewatch.analyzer import analyze
from quakewatch.app import create_app
from quakewatch.collector import Earthquake, save_earthquakes


@pytest.fixture
def client(engine):
    save_earthquakes(engine, [
        Earthquake("ak001", 2.4, "Beluga, Alaska", datetime(2026, 10, 1), -150.6, 61.2, 49.3, None),
        Earthquake("jp001", 4.8, "Off the coast of Japan", datetime(2026, 10, 1), 142.1, 38.3, 10.0, None),
        Earthquake("nc001", 1.2, "6 km NW of The Geysers, CA", datetime(2026, 10, 1), -122.8, 38.8, 2.0, None),
    ])
    return create_app(engine, run_worker=False).test_client()


def test_echoes_user_input(client):
    response = client.get("/?q=Hanoi")

    assert response.status_code == 200
    assert "You searched for: <strong>Hanoi</strong>" in response.text


def test_escapes_user_input(client):
    response = client.get("/?q=<script>alert(1)</script>")

    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text


def test_shows_matching_earthquakes(client):
    response = client.get("/?q=alaska")

    assert "Beluga, Alaska" in response.text
    assert "Off the coast of Japan" not in response.text


def test_search_matches_region_name(client):
    response = client.get("/?q=california")

    assert "The Geysers, CA" in response.text


def test_stats_page(engine, client):
    analyze(engine)

    response = client.get("/stats")

    assert response.status_code == 200
    assert "Alaska" in response.text
    assert "Japan" in response.text


def test_api_earthquakes(client):
    response = client.get("/api/earthquakes?q=japan")

    assert [e["id"] for e in response.get_json()["earthquakes"]] == ["jp001"]


def test_api_stats(engine, client):
    analyze(engine)

    regions = client.get("/api/stats").get_json()["regions"]

    assert {r["region"] for r in regions} == {"Alaska", "Japan", "California"}


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_metrics(client):
    client.get("/?q=alaska")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "quakewatch_request_seconds" in response.text
