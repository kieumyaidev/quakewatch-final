import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, text

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///quakewatch.db")
    # SQLAlchemy needs postgresql://, Render gives postgres://
    return url.replace("postgres://", "postgresql://", 1)


def build_engine(url: str | None = None) -> Engine:
    return create_engine(url or database_url())


def _render(sql: str, engine: Engine) -> str:
    serial = "SERIAL PRIMARY KEY" if engine.dialect.name == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    return sql.replace("{{serial_primary_key}}", serial)


def migrate(engine: Engine) -> list[str]:
    applied_now = []
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(255) PRIMARY KEY)"
        ))
        applied = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in applied:
                continue
            conn.execute(text(_render(path.read_text(), engine)))
            conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:v)"), {"v": path.name})
            applied_now.append(path.name)
    return applied_now


if __name__ == "__main__":
    print("applied:", migrate(build_engine()) or "nothing new")
