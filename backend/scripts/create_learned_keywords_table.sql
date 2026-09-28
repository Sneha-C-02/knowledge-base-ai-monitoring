-- Optional manual migration: Create learned_keywords table
--
-- NOTE: As of this version, SqlAlchemyLearnedKeywordRepository automatically
-- creates this table (and its indexes) the first time it is used, so running
-- this script by hand is no longer required. It is kept here for reference
-- and for DBAs who prefer to manage schema changes explicitly (e.g. via a
-- migration pipeline) rather than relying on runtime auto-creation.
--
-- Stores error/warning-related search terms the system has learned from
-- analyzing uploaded log files, along with how many times each term has
-- been observed. Used to power keyword suggestions in the keyword-focused
-- search UI. instrument_id = 0 means "global" (not tied to one instrument).

CREATE TABLE IF NOT EXISTS learned_keywords (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instrument_id BIGINT NOT NULL DEFAULT 0,
    keyword VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'warning',
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'accepted',
    failure_indicator TEXT,
    sample_line TEXT,
    notes TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_learned_keywords_instrument_keyword
    ON learned_keywords (instrument_id, keyword);

CREATE INDEX IF NOT EXISTS idx_learned_keywords_occurrence_count
    ON learned_keywords (occurrence_count DESC);
