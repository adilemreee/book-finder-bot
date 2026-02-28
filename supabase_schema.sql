-- Supabase SQL Schema for BookFinder Bot
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS searched_books (
    id          BIGSERIAL PRIMARY KEY,
    query       TEXT NOT NULL,
    norm_query  TEXT NOT NULL,
    file_id     TEXT NOT NULL,
    file_name   TEXT,
    file_size   BIGINT,
    source_chat TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    hit_count   INT DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_norm_query ON searched_books(norm_query);
CREATE INDEX IF NOT EXISTS idx_created_at ON searched_books(created_at DESC);

-- RPC function for incrementing hit count
CREATE OR REPLACE FUNCTION increment_hit_count(row_id BIGINT)
RETURNS VOID AS $$
BEGIN
    UPDATE searched_books SET hit_count = hit_count + 1 WHERE id = row_id;
END;
$$ LANGUAGE plpgsql;
