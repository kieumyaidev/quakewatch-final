# QuakeWatch

Collects recent earthquakes from the USGS public API, stores them in a database, analyzes them per region, and lets users search them on a small web site.

## Architecture

- **Collector** (`quakewatch/collector.py`): fetches the USGS GeoJSON feed, saves new earthquakes, publishes an `earthquakes-collected` event.
- **Analyzer** (`quakewatch/analyzer.py`): consumes the event and recomputes per-region stats (count, max and average magnitude, latest time).
- **Worker** (`quakewatch/worker.py`): runs the collector on a schedule and hands events to the analyzer. Runs as its own process, or inside the web process when `RUN_WORKER=true`.
- **Web app** (`quakewatch/app.py`): search page that echoes the input, region report page, JSON API, `/health` and `/metrics` (Prometheus).
- **Messaging** (`quakewatch/messaging.py`): RabbitMQ when `RABBIT_URL` is set, otherwise a queue table in the database.
- **Database**: PostgreSQL in production, SQLite by default for local work. SQL migrations in `migrations/`.

## Endpoints

| Path | Description |
|---|---|
| `/?q=alaska` | Search page |
| `/stats` | Region report |
| `/api/earthquakes?q=alaska` | Search as JSON |
| `/api/stats` | Region stats as JSON |
| `/health` | Health check (also checks the database) |
| `/metrics` | Prometheus metrics |

## Run locally

```shell
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python -m quakewatch.db          # run migrations
python -m quakewatch.collector   # fetch once and publish an event
python -m quakewatch.worker      # collect every 15 minutes and run the analyzer
python -m quakewatch.app         # web app on http://localhost:5000
```

To use Postgres and RabbitMQ locally:

```shell
docker compose up -d
export DATABASE_URL=postgresql://quakewatch:quakewatch@localhost:5433/quakewatch
export RABBIT_URL=amqp://guest:guest@localhost:5673/
```

## Tests

```shell
python -m pytest tests/unit          # unit tests, SQLite, USGS mocked
python -m pytest tests/integration   # full pipeline, uses DATABASE_URL and RABBIT_URL if set
```

## CI/CD and deployment

GitHub Actions (`.github/workflows/ci.yml`) runs unit and integration tests against Postgres and RabbitMQ on every push. On `main`, after tests pass, it calls the Render deploy hook (`RENDER_DEPLOY_HOOK_URL` secret). `render.yaml` creates the free Postgres database and the web service from the `Dockerfile`.
