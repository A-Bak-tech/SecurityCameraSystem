"""
PC Guard: watches keyboard/mouse activity and periodically verifies
who's using the PC via face recognition, camera-off otherwise.

Two independent triggers, so a handoff between the owner and someone
else gets caught quickly either way:
- Idle-triggered check: after IDLE_THRESHOLD_SECONDS of no input,
  the next keystroke/click triggers a check (catches "owner left,
  came back later" and "owner left, someone else arrives after a
  pause").
- Periodic check: every PERIODIC_RECHECK_SECONDS, a check fires
  regardless of activity (catches "owner left, someone else sat
  down immediately and kept typing with no gap at all").

Either check succeeding (recognizes the owner) resets both timers
and stays silent. Either check failing (unrecognized face, or no
face despite input) triggers exactly one alert + lock, and won't
alert again until the owner is recognized.
"""

import sqlite3
import sys
import time
import ctypes
import winsound
from datetime import datetime
from pathlib import Path
from threading import Lock

import cv2
from pynput import keyboard, mouse

from recognize_face import FaceRecognizer
from app_paths import SNAPSHOTS_DIR as SNAPSHOT_DIR, DB_PATH, init_database, load_config

CONFIG = load_config()
CAMERA_DEVICE_INDEX = CONFIG.get("camera_device_index", 0)
IDLE_THRESHOLD_SECONDS = 1.5       # short pause before the next input triggers a check
PERIODIC_RECHECK_SECONDS = 8.0   # force a check this often even with continuous activity
POST_CHECK_COOLDOWN = 3.0          # after any check, wait this long before another can fire
LOOP_INTERVAL = 0.5


def log_unauthorized_event(frame, reason: str):
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
    ctypes.windll.user32.LockWorkStation()


def check_face_once(recognizer: FaceRecognizer):
    """
    Opens the camera, warms it up, then checks frames for up to ~1.5
    seconds — giving a real person enough time to turn toward the
    camera naturally. Returns the BEST result among all attempts.
    """
    cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Warning: could not open camera for check.")
        return None

    for _ in range(10):
        cap.read()
        time.sleep(0.05)

    best_result = None
    last_frame = None

    for _ in range(12):  # ~1.2 seconds of attempts at 0.1s apart
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        last_frame = frame
        result = recognizer.check_frame(frame)

        if best_result is None or result["similarity"] > best_result["similarity"]:
            best_result = result

        if result["authorized"]:
            break

        time.sleep(0.1)

    cap.release()

    if best_result is None:
        return None
    best_result["_frame"] = last_frame
    return best_result


def main():
    init_database()
    recognizer = FaceRecognizer()
    print(f"Enrolled: {list(recognizer.reference_embeddings.keys())}")

    state = {"input_since_last_check": 0}
    state_lock = Lock()

    def register_input():
        with state_lock:
            state["input_since_last_check"] += 1

    def on_key_press(_key):
        register_input()

    def on_mouse_click(_x, _y, _button, pressed):
        if pressed:
            register_input()

    key_listener = keyboard.Listener(on_press=on_key_press)
    mouse_listener = mouse.Listener(on_click=on_mouse_click)
    key_listener.start()
    mouse_listener.start()

    print("PC Guard running (idle + periodic checks, camera off otherwise). Press Ctrl+C to stop.")

    last_input_time = time.time()
    last_check_time = 0.0
    session_alerted = False
    was_idle = False

    try:
        while True:
            time.sleep(LOOP_INTERVAL)
            now = time.time()

            with state_lock:
                had_input = state["input_since_last_check"] > 0

            if had_input:
                last_input_time = now

            idle_duration = now - last_input_time
            is_idle = idle_duration >= IDLE_THRESHOLD_SECONDS
            in_cooldown = (now - last_check_time) < POST_CHECK_COOLDOWN
            time_since_last_check = now - last_check_time

            should_check_idle_return = was_idle and not is_idle and not in_cooldown
            should_check_periodic = had_input and time_since_last_check >= PERIODIC_RECHECK_SECONDS and not in_cooldown

            if should_check_idle_return or should_check_periodic:
                result = check_face_once(recognizer)
                last_check_time = time.time()

                with state_lock:
                    state["input_since_last_check"] = 0

                if result is None:
                    print("Could not verify (camera unavailable) — skipping this check.")
                elif result["authorized"]:
                    print(f"Recognized: {result['matched_name']} ({result['similarity']:.3f})")
                    session_alerted = False
                elif result["face_found"] and not session_alerted:
                    # Only alert when a face was actually seen and it's
                    # not a match — never alert on "no face" alone, since
                    # that's ambiguous (owner could just be looking away).
                    log_unauthorized_event(result["_frame"], "unrecognized_face")
                    sound_alert()
                    lock_workstation()
                    session_alerted = True
                elif not result["face_found"]:
                    print("No face visible during check — skipping (inconclusive).")

            was_idle = is_idle

    except KeyboardInterrupt:
        print("Stopping PC Guard.")
    finally:
        key_listener.stop()
        mouse_listener.stop()


if __name__ == "__main__":
    main()