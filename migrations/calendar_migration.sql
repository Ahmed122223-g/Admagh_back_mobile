-- ============================================
-- Database Migration: Remove Google Calendar Integration
-- ============================================

-- Drop Google Calendar columns from users table
ALTER TABLE users DROP COLUMN IF EXISTS google_access_token;
ALTER TABLE users DROP COLUMN IF EXISTS google_refresh_token;
ALTER TABLE users DROP COLUMN IF EXISTS google_token_expiry;

-- Drop google_event_id from tasks table
ALTER TABLE tasks DROP COLUMN IF EXISTS google_event_id;

-- ============================================
-- Database Migration: Create Custom Calendar System
-- ============================================

-- Create calendar_events table
CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    task_id INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notification_sent BOOLEAN DEFAULT FALSE,
    
    -- Foreign key constraints
    CONSTRAINT fk_calendar_user 
        FOREIGN KEY (user_id) REFERENCES users(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_calendar_task 
        FOREIGN KEY (task_id) REFERENCES tasks(id) 
        ON DELETE CASCADE,
    
    -- Unique constraint: one task can only be scheduled once
    CONSTRAINT unique_task_schedule UNIQUE (task_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_calendar_user_id ON calendar_events(user_id);
CREATE INDEX IF NOT EXISTS idx_calendar_start_time ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_notification ON calendar_events(notification_sent, start_time);

-- ============================================
-- Verification Queries
-- ============================================

-- Verify tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('users', 'tasks', 'calendar_events');

-- Verify columns were dropped
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name IN ('google_access_token', 'google_refresh_token', 'google_token_expiry');

-- Should return empty result (0 rows)
