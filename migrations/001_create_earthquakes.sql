CREATE TABLE IF NOT EXISTS earthquakes (
    id          VARCHAR(64) PRIMARY KEY,
    magnitude   REAL,
    place       VARCHAR(255),
    occurred_at TIMESTAMP NOT NULL,
    longitude   REAL NOT NULL,
    latitude    REAL NOT NULL,
    depth_km    REAL,
    url         VARCHAR(512),
    collected_at TIMESTAMP NOT NULL
);
