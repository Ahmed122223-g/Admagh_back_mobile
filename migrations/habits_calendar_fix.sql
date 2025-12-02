ALTER TABLE calendar_events 
ALTER COLUMN task_id DROP NOT NULL;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'calendar_events' AND column_name = 'habit_id'
    ) THEN
        ALTER TABLE calendar_events ADD COLUMN habit_id INTEGER;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'calendar_events' AND column_name = 'event_type'
    ) THEN
        ALTER TABLE calendar_events ADD COLUMN event_type VARCHAR(20) DEFAULT 'task';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_calendar_habit'
    ) THEN
        ALTER TABLE calendar_events
        ADD CONSTRAINT fk_calendar_habit
        FOREIGN KEY (habit_id) REFERENCES habits(id)
        ON DELETE CASCADE;
    END IF;
END $$;

ALTER TABLE calendar_events
DROP CONSTRAINT IF EXISTS unique_task_schedule;

ALTER TABLE calendar_events
DROP CONSTRAINT IF EXISTS chk_task_or_habit;

ALTER TABLE calendar_events
ADD CONSTRAINT chk_task_or_habit
CHECK (
    (task_id IS NOT NULL AND habit_id IS NULL) OR
    (task_id IS NULL AND habit_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_calendar_habit_id ON calendar_events(habit_id);

CREATE INDEX IF NOT EXISTS idx_calendar_event_type ON calendar_events(event_type);

SELECT 
    column_name, 
    is_nullable, 
    data_type,
    column_default
FROM information_schema.columns 
WHERE table_name = 'calendar_events' 
AND column_name IN ('task_id', 'habit_id', 'event_type')
ORDER BY column_name;
