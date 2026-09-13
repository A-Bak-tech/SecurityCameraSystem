# SecurityCameraSystem

A motion-triggered security camera system combining C++ (capture, motion
detection, recording), SQLite (event logging), and Python (offline object
classification via YOLOv5).

## Architecture

**C++ core** handles the live pipeline: opens a camera, detects motion via
background subtraction, saves snapshots and video clips, verifies recordings,
and automatically reconnects if the camera disconnects.

**SQLite** stores a structured event log (`db/events.db`) — every motion
event, snapshot, and recording is written as a row, queryable independently
of the log file.

**Python** reads snapshot events from the database, runs YOLOv5 object
detection on each image, and writes classification results (person /
vehicle / animal / other) back into the database.