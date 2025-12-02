-- Drop the restrictive constraint
ALTER TABLE calendar_events DROP CONSTRAINT IF EXISTS chk_task_or_habit;

-- Add a more flexible constraint that allows challenges to have null task_id and habit_id
ALTER TABLE calendar_events ADD CONSTRAINT chk_event_content CHECK (
    (event_type = 'task' AND task_id IS NOT NULL) OR
    (event_type = 'habit' AND habit_id IS NOT NULL) OR
    (event_type IN ('challenge', 'event'))
);
