CREATE TABLE IF NOT EXISTS messages (
    id           {{serial_primary_key}},
    queue        VARCHAR(255) NOT NULL,
    body         TEXT NOT NULL,
    created_at   TIMESTAMP NOT NULL,
    processed_at TIMESTAMP
);
