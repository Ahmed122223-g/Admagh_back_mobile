-- Add individual_trophies column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS individual_trophies INTEGER DEFAULT 0;
