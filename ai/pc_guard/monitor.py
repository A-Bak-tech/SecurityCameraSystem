"""
PC Guard: tracks keyboard/mouse activity continuously (no camera use).
When input resumes after a period of inactivity (meaning someone just
sat down at the PC), the camera turns on for a single face check, then
turns off immediately — no continuous camera use, no light staying on.

If the single check confirms the owner, it goes back to silently
tracking input with the camera off. If it's an unrecognized face (or
no face at all), it alerts and locks the workstation.
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

# --- Configuration ---
CAMERA_DEVICE_INDEX = 1
IDLE_THRESHOLD_SECONDS = 60.0     # no input for this long = owner considered "away"
POST_CHECK_COOLDOWN = 5.0         # after any check, ignore further input briefly (avoids re-triggering mid-typing)
LOOP_INTERVAL = 1.0               # how often to check the idle clock (camera stays off during this)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = PROJECT_ROOT / "snapshots"
DB_PATH = PROJECT_ROOT / "db" / "events.db"

SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


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
    Opens the camera, lets it warm up (auto-exposure needs a moment),
    then checks several frames and returns the BEST result among them —
    if any frame recognizes the owner, that counts as authorized. This
    avoids a single bad frame (dark/blurry, right as the camera opens)
    from wrongly locking the owner out.
    """
    cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX)
    if not cap.isOpened():
        print("Warning: could not open camera for check.")
        return None

    # Warm-up: read and discard several frames while auto-exposure settles.
    for _ in range(10):
        cap.read()
        time.sleep(0.05)

    # Now take a few real attempts, spaced slightly apart.
    best_result = None
    last_frame = None

    for _ in range(4):
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        last_frame = frame
        result = recognizer.check_frame(frame)

        if best_result is None or result["similarity"] > best_result["similarity"]:
            best_result = result

        if result["authorized"]:
            break  # found a clean match, no need to keep trying

        time.sleep(0.1)

    cap.release()

    if best_result is None:
        return None

    best_result["_frame"] = last_frame
    return best_result


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Run the C++ program at least once first.")
        sys.exit(1)

    recognizer = FaceRecognizer()
    print(f"Enrolled: {list(recognizer.reference_embeddings.keys())}")

    state = {"last_input_time": time.time()}
    state_lock = Lock()

    def mark_input():
        with state_lock:
            state["last_input_time"] = time.time()

    def on_key_press(_key):
        mark_input()

    def on_mouse_click(_x, _y, _button, pressed):
        if pressed:
            mark_input()

    key_listener = keyboard.Listener(on_press=on_key_press)
    mouse_listener = mouse.Listener(on_click=on_mouse_click)
    key_listener.start()
    mouse_listener.start()

    print("PC Guard running (idle-triggered, camera off unless checking). Press Ctrl+C to stop.")

    was_idle = False
    last_check_time = 0.0

    try:
        while True:
            time.sleep(LOOP_INTERVAL)
            now = time.time()

            with state_lock:
                idle_duration = now - state["last_input_time"]

            is_idle = idle_duration >= IDLE_THRESHOLD_SECONDS
            in_cooldown = (now - last_check_time) < POST_CHECK_COOLDOWN

            # Trigger exactly on the transition: was idle, input just resumed.
            if was_idle and not is_idle and not in_cooldown:
                print("Input resumed after idle period — checking face...")
                result = check_face_once(recognizer)
                last_check_time = time.time()

                if result is None:
                    print("Could not verify (camera unavailable) — skipping this check.")
                elif result["authorized"]:
                    print(f"Recognized: {result['matched_name']} ({result['similarity']:.3f})")
                else:
                    reason = "unrecognized_face" if result["face_found"] else "no_face_but_input"
                    log_unauthorized_event(result["_frame"], reason)
                    sound_alert()
                    lock_workstation()

            was_idle = is_idle

    except KeyboardInterrupt:
        print("Stopping PC Guard.")
    finally:
        key_listener.stop()
        mouse_listener.stop()


if __name__ == "__main__":
    main()