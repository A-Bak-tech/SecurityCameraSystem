"""
PC Guard: watches the webcam and keyboard/mouse for unauthorized use
while the authorized user isn't present, alerting with a sound and
logging the event into the shared SQLite database.

Two independent triggers, since they need different sensitivity:
- Face trigger: fast. A stranger's face appearing and persisting for
  FACE_PERSISTENCE_SECONDS is a strong, quick signal on its own.
- Input trigger: slow. The owner naturally looks away from the webcam
  constantly while typing, so "no recognized face" alone isn't
  meaningful for a while — INPUT_AWAY_GRACE is deliberately long, and
  MIN_INPUT_EVENTS requires sustained typing, not a stray keystroke.

Either trigger fires at most once per "away session," which ends the
moment the owner's face is recognized again.
"""

import sqlite3
import sys
import time
import winsound
from datetime import datetime
from pathlib import Path
from threading import Lock
import ctypes

import cv2
from pynput import keyboard, mouse

from recognize_face import FaceRecognizer

# --- Configuration ---
CAMERA_DEVICE_INDEX = 1

FACE_AWAY_GRACE = 1.5             # seconds before a stranger's face check even starts mattering
FACE_PERSISTENCE_SECONDS = 0.8    # stranger's face must persist this long to trigger

INPUT_AWAY_GRACE = 6.0            # seconds of no recognized face before typing is treated as suspicious
MIN_INPUT_EVENTS = 5              # keystrokes/clicks required during that window, not just one or two

POST_RETURN_COOLDOWN = 2.5        # seconds after being recognized before a new session can arm at all
LOOP_INTERVAL = 0.1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = PROJECT_ROOT / "snapshots"
DB_PATH = PROJECT_ROOT / "db" / "events.db"

SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def log_unauthorized_event(frame, reason: str):
    """Saves a snapshot and writes an event row to the shared database."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"pcguard_{timestamp}.jpg"
    full_path = SNAPSHOT_DIR / filename
    cv2.imwrite(str(full_path), frame)

    relative_path = f"snapshots/{filename}"
    iso_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            INSERT INTO events (event_type, file_path, camera_device_index, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (f"unauthorized_access:{reason}", relative_path, CAMERA_DEVICE_INDEX, iso_timestamp),
        )
        conn.commit()
    finally:
        conn.close()

    print(f"ALERT ({reason}): saved {relative_path}, logged to database.")


def sound_alert():
    for _ in range(3):
        winsound.Beep(1000, 200)
        time.sleep(0.1)

def lock_workstation():
    """Locks the Windows session immediately, exactly like pressing Win + L.
    The intruder sees the login screen and cannot type into the session
    at all; unlocking requires the normal Windows account password or PIN.
    """
    ctypes.windll.user32.LockWorkStation()


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Run the C++ program at least once first.")
        sys.exit(1)

    cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX)
    if not cap.isOpened():
        print("Failed to open camera.")
        sys.exit(1)

    recognizer = FaceRecognizer()

    state = {
        "tracking_input": False,   # only True once we're past INPUT_AWAY_GRACE
        "input_event_count": 0,
    }
    state_lock = Lock()

    def register_input_event():
        with state_lock:
            if state["tracking_input"]:
                state["input_event_count"] += 1

    def on_key_press(_key):
        register_input_event()

    def on_mouse_click(_x, _y, _button, pressed):
        if pressed:
            register_input_event()

    key_listener = keyboard.Listener(on_press=on_key_press)
    mouse_listener = mouse.Listener(on_click=on_mouse_click)
    key_listener.start()
    mouse_listener.start()

    print("PC Guard running. Press Ctrl+C to stop.")

    authorized_last_seen = time.time()
    unauthorized_face_start = None
    session_alerted = False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.5)
                continue

            result = recognizer.check_frame(frame)
            now = time.time()

            if result["authorized"]:
                authorized_last_seen = now
                unauthorized_face_start = None
                session_alerted = False
                with state_lock:
                    state["tracking_input"] = False
                    state["input_event_count"] = 0
            elif result["face_found"]:
                if unauthorized_face_start is None:
                    unauthorized_face_start = now
            else:
                unauthorized_face_start = None

            time_since_authorized = now - authorized_last_seen
            in_cooldown = time_since_authorized < POST_RETURN_COOLDOWN

            face_check_active = (time_since_authorized > FACE_AWAY_GRACE) and not in_cooldown
            input_check_active = (time_since_authorized > INPUT_AWAY_GRACE) and not in_cooldown

            with state_lock:
                if input_check_active and not state["tracking_input"]:
                    state["tracking_input"] = True
                    state["input_event_count"] = 0
                elif not input_check_active:
                    state["tracking_input"] = False
                    state["input_event_count"] = 0
                current_input_count = state["input_event_count"]

            print(f"authorized={result['authorized']} face_found={result['face_found']} "
                  f"since_auth={time_since_authorized:.1f}s in_cooldown={in_cooldown} "
                  f"input_count={current_input_count}", flush=True)

            if not session_alerted:
                unauthorized_face_persisted = (
                    face_check_active
                    and unauthorized_face_start is not None
                    and (now - unauthorized_face_start) >= FACE_PERSISTENCE_SECONDS
                )
                sustained_input = input_check_active and current_input_count >= MIN_INPUT_EVENTS

                if unauthorized_face_persisted or sustained_input:
                    reason = "unrecognized_face" if unauthorized_face_persisted else "input_activity"
                    log_unauthorized_event(frame, reason)
                    sound_alert()
                    lock_workstation()
                    session_alerted = True

            time.sleep(LOOP_INTERVAL)

    except KeyboardInterrupt:
        print("Stopping PC Guard.")
    finally:
        cap.release()
        key_listener.stop()
        mouse_listener.stop()


if __name__ == "__main__":
    main()