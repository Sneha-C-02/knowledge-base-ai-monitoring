-- Migration: Create monitored_log_files table
-- Run this against your Supabase PostgreSQL database

CREATE TABLE IF NOT EXISTS monitored_log_files (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrument_id BIGINT NOT NULL REFERENCES instruments(id),
    filename VARCHAR NOT NULL,
    total_lines_analyzed INTEGER NOT NULL DEFAULT 0,
    full_context_summary TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_monitored_log_files_instrument_id
    ON monitored_log_files(instrument_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_monitored_log_files_instrument_filename
    ON monitored_log_files(instrument_id, filename);
