CREATE TABLE IF NOT EXISTS region_stats (
    region           VARCHAR(255) PRIMARY KEY,
    quake_count      INTEGER NOT NULL,
    max_magnitude    REAL,
    avg_magnitude    REAL,
    last_occurred_at TIMESTAMP,
    analyzed_at      TIMESTAMP NOT NULL
);
