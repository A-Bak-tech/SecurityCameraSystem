-- Events table: one row per motion/snapshot/recording event.
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,       -- 'motion_start', 'motion_stop', 'snapshot', 'recording_start', 'recording_stop'
    file_path TEXT,                 -- path to snapshot/recording file, NULL for motion events
    camera_device_index INTEGER NOT NULL,
    created_at TEXT NOT NULL        -- ISO 8601 timestamp
);

-- Detections table: AI classification results for a snapshot/recording,
-- populated later by the Python detector/classifier.
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    label TEXT NOT NULL,            -- 'person', 'vehicle', 'animal', etc.
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id)
);