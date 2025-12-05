-- Add rank column to challenge_participants table
ALTER TABLE challenge_participants ADD COLUMN IF NOT EXISTS rank INTEGER DEFAULT NULL;

-- Create index for faster rank queries
CREATE INDEX IF NOT EXISTS idx_challenge_participants_rank ON challenge_participants(rank);
CREATE INDEX IF NOT EXISTS idx_challenge_participants_user_rank ON challenge_participants(user_id, rank);
