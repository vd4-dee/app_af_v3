CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    config_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    next_run_time TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    session_id TEXT
);