-- Fix user_id type in habits table to support large IDs
ALTER TABLE habits ALTER COLUMN user_id TYPE BIGINT;
