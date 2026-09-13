-- Retention maintenance queries.
-- Run manually, or adapt into a scheduled cleanup script later.

-- Preview: events older than 30 days (run this first to see what would be deleted).
SELECT * FROM events
WHERE created_at < datetime('now', '-30 days')
ORDER BY created_at ASC;

-- Delete detections tied to events older than 30 days (delete this table's
-- rows first due to the foreign key on event_id).
DELETE FROM detections
WHERE event_id IN (
    SELECT id FROM events WHERE created_at < datetime('now', '-30 days')
);

-- Delete the events themselves.
DELETE FROM events
WHERE created_at < datetime('now', '-30 days');

-- Note: this only removes database rows, not the actual .jpg/.avi files on
-- disk. A future enhancement could read file_path from the preview query
-- above and delete those files before running the DELETE statements.