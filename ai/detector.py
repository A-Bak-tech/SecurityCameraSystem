"""
Offline snapshot classifier for SecurityCameraSystem.

Finds snapshot events in the SQLite database that haven't been
classified yet, runs YOLOv5 object detection on each one, and writes
the results into the detections table.

Run manually after some snapshots have been captured:
    python detector.py
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch

from classifier import classify_label

# Paths are relative to the project root, matching where the C++ side
# reads/writes (db/events.db, snapshots/).
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "events.db"
CONFIDENCE_THRESHOLD = 0.4  # ignore detections below this confidence


def get_unclassified_snapshots(conn: sqlite3.Connection):
    """
    Returns a list of (event_id, file_path) for snapshot events that
    don't yet have a corresponding row in the detections table.
    """
    cursor = conn.execute(
        """
        SELECT e.id, e.file_path
        FROM events e
        LEFT JOIN detections d ON d.event_id = e.id
        WHERE e.event_type = 'snapshot' AND d.id IS NULL
        """
    )
    return cursor.fetchall()


def insert_detection(conn: sqlite3.Connection, event_id: int, label: str, confidence: float):
    conn.execute(
        """
        INSERT INTO detections (event_id, label, confidence, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (event_id, label, confidence, datetime.now(timezone.utc).isoformat()),
    )


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Run the C++ program first to create it.")
        sys.exit(1)

    print("Loading YOLOv5 model (first run downloads weights, may take a minute)...")
    model = torch.hub.load("ultralytics/yolov5", "yolov5s", trust_repo=True)
    model.conf = CONFIDENCE_THRESHOLD

    conn = sqlite3.connect(DB_PATH)

    try:
        pending = get_unclassified_snapshots(conn)
        if not pending:
            print("No unclassified snapshots found.")
            return

        print(f"Found {len(pending)} unclassified snapshot(s).")

        for event_id, file_path in pending:
            if not file_path:
                print(f"  [{event_id}] has no file_path recorded, skipping.")
                continue

            full_path = Path(__file__).resolve().parent.parent / file_path

            if not full_path.exists():
                print(f"  [{event_id}] file missing: {full_path}, skipping.")
                continue

            results = model(str(full_path))
            detections = results.pandas().xyxy[0]  # one row per detected object

            if detections.empty:
                insert_detection(conn, event_id, "none", 0.0)
                print(f"  [{event_id}] {file_path}: no objects detected.")
                continue

            for _, row in detections.iterrows():
                category = classify_label(row["name"])
                confidence = float(row["confidence"])
                insert_detection(conn, event_id, category, confidence)
                print(f"  [{event_id}] {file_path}: {category} ({confidence:.2f})")

        conn.commit()

    finally:
        conn.close()


if __name__ == "__main__":
    main()