-- Recent events with their AI classification results, if any.
SELECT
    e.id,
    e.event_type,
    e.file_path,
    e.created_at,
    d.label,
    d.confidence
FROM events e
LEFT JOIN detections d ON d.event_id = e.id
ORDER BY e.id DESC
LIMIT 20;

-- Count of detections by category (useful summary stat).
SELECT label, COUNT(*) AS count
FROM detections
GROUP BY label
ORDER BY count DESC;

-- All recordings that failed verification (should be empty on a healthy system).
SELECT * FROM events
WHERE event_type = 'recording_stop'
  AND file_path NOT IN (
      SELECT file_path FROM events WHERE event_type = 'recording_stop'
  );