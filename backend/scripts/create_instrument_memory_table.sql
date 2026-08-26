-- Migration: Create instrument_memory table
-- Run this against your Supabase PostgreSQL database

CREATE TABLE IF NOT EXISTS instrument_memory (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrument_id BIGINT NOT NULL REFERENCES instruments(id),
    instrument_name VARCHAR NOT NULL,
    analysis_timestamp TIMESTAMPTZ NOT NULL,
    log_filename VARCHAR NOT NULL,
    critical_incidents INTEGER NOT NULL DEFAULT 0,
    warnings INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    healthy_apps INTEGER NOT NULL DEFAULT 0,
    ai_summary TEXT NOT NULL,
    raw_issues_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_instrument_memory_instrument_id 
    ON instrument_memory(instrument_id);

CREATE INDEX IF NOT EXISTS idx_instrument_memory_timestamp 
    ON instrument_memory(analysis_timestamp DESC);
