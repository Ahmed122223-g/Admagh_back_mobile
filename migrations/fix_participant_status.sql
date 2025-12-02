-- Drop the restrictive constraint on challenge_participants status
ALTER TABLE challenge_participants DROP CONSTRAINT IF EXISTS challenge_participants_status_check;

-- Add updated constraint allowing 'active' and 'finished' statuses
ALTER TABLE challenge_participants ADD CONSTRAINT challenge_participants_status_check CHECK (status IN ('invited', 'accepted', 'rejected', 'active', 'finished'));
