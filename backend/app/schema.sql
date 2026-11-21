-- Vector width matches text-embedding-3-small and EMBEDDING_DIMENSIONS (1536).
-- There is no ANN index: this corpus is a few dozen chunks, so exact ORDER BY is enough.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    section_heading TEXT NOT NULL,
    section_path TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    embedding vector(1536) NOT NULL
);

-- Daily and hourly counters for the public demo. One row per scope, route, and window.
CREATE TABLE IF NOT EXISTS api_usage (
    scope TEXT NOT NULL,
    route TEXT NOT NULL,
    window_kind TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    hits INTEGER NOT NULL,
    PRIMARY KEY (scope, route, window_kind, window_start)
);
