"""
Central path definitions for PC Guard. All app data (enrolled faces,
settings, snapshots, event log) lives under the user's AppData folder,
independent of wherever the app itself is installed — this is what
lets PC Guard run as a standalone app for anyone, not just tied to
this specific project's folder structure.
"""

import os
import sys
import sqlite3
import json
from pathlib import Path

APP_NAME = "PCGuard"


def get_app_data_dir() -> Path:
    """Returns %APPDATA%\\PCGuard, creating it if needed."""
    appdata = os.getenv("APPDATA")
    if appdata is None:
        # Fallback, shouldn't normally happen on Windows
        appdata = str(Path.home() / "AppData" / "Roaming")
    app_dir = Path(appdata) / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_resource_dir() -> Path:
    """
    Returns the folder containing bundled resources (the .onnx model
    files). Works both when running from source (this file's folder)
    and when packaged by PyInstaller (sys._MEIPASS, the temp folder
    PyInstaller extracts bundled data into at runtime).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


APP_DATA_DIR = get_app_data_dir()
ENROLLED_FACES_DIR = APP_DATA_DIR / "enrolled_faces"
SNAPSHOTS_DIR = APP_DATA_DIR / "snapshots"
DB_PATH = APP_DATA_DIR / "events.db"
CONFIG_PATH = APP_DATA_DIR / "config.json"

ENROLLED_FACES_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

RESOURCE_DIR = get_resource_dir()
DETECTOR_MODEL = RESOURCE_DIR / "face_detection_yunet.onnx"
RECOGNIZER_MODEL = RESOURCE_DIR / "face_recognition_sface.onnx"


def init_database():
    """Creates PC Guard's own lightweight event log — no dependency on
    the SecurityCameraSystem C++ project's schema.sql."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                file_path TEXT,
                camera_device_index INTEGER,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


DEFAULT_CONFIG = {
    "camera_device_index": 0,
    "idle_threshold_seconds": 60.0,
    "sound_enabled": True,
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r") as f:
            saved = json.load(f)
        config = dict(DEFAULT_CONFIG)
        config.update(saved)
        return config
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def has_any_enrolled_faces() -> bool:
    return any(ENROLLED_FACES_DIR.glob("*.npy"))


STATUS_PATH = APP_DATA_DIR / "status.json"


def write_status(running: bool):
    with open(STATUS_PATH, "w") as f:
        json.dump({"running": running}, f)


def read_status() -> bool:
    if not STATUS_PATH.exists():
        return False
    try:
        with open(STATUS_PATH, "r") as f:
            return json.load(f).get("running", False)
    except Exception:
        return False
