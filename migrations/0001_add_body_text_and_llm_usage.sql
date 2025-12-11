-- Migration: Add body_text column to emails and create llm_usage table
-- Date: 2025-12-11
-- Description: 
--   1. Add body_text column to store full email body (HTML-stripped)
--   2. Create llm_usage table to track Gemini token usage per email

-- Add body_text column to emails table
ALTER TABLE emails ADD COLUMN body_text TEXT;

-- Create llm_usage table for token tracking
CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    model TEXT NOT NULL,
    operation TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES emails(id)
);

-- Create index for efficient lookups by email_id
CREATE INDEX IF NOT EXISTS idx_llm_usage_email_id ON llm_usage(email_id);
