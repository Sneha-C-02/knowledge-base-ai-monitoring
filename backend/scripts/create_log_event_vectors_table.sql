-- ============================================================
-- Log Event Vectors Table
-- Run this in your Supabase SQL Editor once.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS log_event_vectors (
    id               BIGSERIAL PRIMARY KEY,
    instrument_id    BIGINT REFERENCES instruments(id) ON DELETE CASCADE,
    log_filename     TEXT NOT NULL,
    severity         TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    component        TEXT,                        -- e.g. 'EngineerServer'
    cleaned_text     TEXT NOT NULL,               -- distilled semantic text
    raw_log_line     TEXT NOT NULL,               -- original line for display
    matched_patterns TEXT[],                      -- e.g. '{write_fail, rio_status}'
    event_embedding  VECTOR(384),                 -- embedding of cleaned_text
    captured_at      TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index for fast approximate nearest-neighbour cosine search
-- Adjust lists based on expected row count (100 is a good default for < 1M rows)
CREATE INDEX IF NOT EXISTS log_event_vectors_embedding_idx
    ON log_event_vectors
    USING ivfflat (event_embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index for fast filtering by instrument
CREATE INDEX IF NOT EXISTS log_event_vectors_instrument_idx
    ON log_event_vectors (instrument_id);

-- Index for severity filtering
CREATE INDEX IF NOT EXISTS log_event_vectors_severity_idx
    ON log_event_vectors (severity);
