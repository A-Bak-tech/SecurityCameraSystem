"""
PC Guard tray icon: a lightweight wrapper that starts/stops monitor.py
as a separate process. Runs in its own process with no cv2 import at
all, avoiding a DLL conflict between OpenCV and pystray on Windows.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image
import pystray

from app_paths import SNAPSHOTS_DIR, APP_DATA_DIR, init_database, write_status

SCRIPT_DIR = Path(__file__).resolve().parent
MONITOR_SCRIPT = SCRIPT_DIR / "monitor.py"
ENROLL_SCRIPT = SCRIPT_DIR / "enroll_face.py"
DASHBOARD_SCRIPT = SCRIPT_DIR / "dashboard.py"
ICON_PATH = SCRIPT_DIR / "pcguard_icon.ico"

state = {"process": None}


def make_icon_image(color: str) -> Image.Image:
    # Loads the real icon file instead of drawing a plain circle.
    # 'color' is kept as a parameter for compatibility with existing
    # calls, but the icon itself no longer changes color — status is
    # now visible through the dashboard's Status tab instead.
    return Image.open(ICON_PATH)


def is_running() -> bool:
    return state["process"] is not None and state["process"].poll() is None


def start_monitor(icon, item):
    if is_running():
        return
    state["process"] = subprocess.Popen(
        [sys.executable, str(MONITOR_SCRIPT)],
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    icon.icon = make_icon_image("green")
    write_status(True)


def stop_monitor(icon, item):
    if is_running():
        state["process"].terminate()
        state["process"] = None
    icon.icon = make_icon_image("gray")
    write_status(False)


def is_active(item) -> bool:
    return is_running()


def enroll_new_face(icon, item):
    subprocess.Popen(
        [sys.executable, str(SCRIPT_DIR / "setup_wizard.py"), "--add-person"],
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def open_dashboard(icon, item):
    subprocess.Popen(
        [sys.executable, str(DASHBOARD_SCRIPT)],
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def open_snapshots_folder(icon, item):
    subprocess.Popen(f'explorer "{SNAPSHOTS_DIR}"')


def open_appdata_folder(icon, item):
    subprocess.Popen(f'explorer "{APP_DATA_DIR}"')


def quit_app(icon, item):
    stop_monitor(icon, item)
    icon.stop()


def main():
    init_database()

    menu = pystray.Menu(
        pystray.MenuItem("Running", lambda icon, item: None, checked=is_active, enabled=False),
        pystray.MenuItem("Open Dashboard", open_dashboard),
        pystray.MenuItem("Start", start_monitor),
        pystray.MenuItem("Stop", stop_monitor),
        pystray.MenuItem("Enroll New Face", enroll_new_face),
        pystray.MenuItem("Open Snapshots Folder", open_snapshots_folder),
        pystray.MenuItem("Open App Data Folder", open_appdata_folder),
        pystray.MenuItem("Quit", quit_app),
    )

    icon = pystray.Icon("PC Guard", make_icon_image("gray"), "PC Guard", menu)
    icon.run()


if __name__ == "__main__":
    import traceback
    try:
        print("Starting tray_app.py...", flush=True)
        main()
        print("main() returned — this should only happen after Quit is clicked.", flush=True)
    except Exception:
        print("CRASHED:", flush=True)
        traceback.print_exc()