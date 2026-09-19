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

from app_paths import SNAPSHOTS_DIR, APP_DATA_DIR, init_database, write_status, has_any_enrolled_faces

if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(sys._MEIPASS)
else:
    SCRIPT_DIR = Path(__file__).resolve().parent
    RESOURCE_DIR = SCRIPT_DIR

MONITOR_SCRIPT = SCRIPT_DIR / "monitor.exe"
DASHBOARD_SCRIPT = SCRIPT_DIR / "dashboard.exe"
SETUP_WIZARD_SCRIPT = SCRIPT_DIR / "setup_wizard.exe"
ICON_PATH = RESOURCE_DIR / "pcguard_icon.ico"

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

    if not has_any_enrolled_faces():
        # No one enrolled yet — send them through setup instead of
        # letting monitor.exe crash looking for a face that doesn't exist.
        subprocess.Popen(
            [str(SETUP_WIZARD_SCRIPT)],
            cwd=str(SCRIPT_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return

    state["process"] = subprocess.Popen(
        [str(MONITOR_SCRIPT)],
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    icon.icon = make_icon_image("green")
    write_status(True)


def stop_monitor(icon, item):
    # Kill by name, not just the tracked process — an orphaned monitor.exe
    # from a previous session (crash, rebuild, manual launch) would
    # otherwise keep running with the camera live, invisible to this
    # tray instance's own state tracking.
    subprocess.run(
        ["taskkill", "/IM", "monitor.exe", "/F"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    state["process"] = None
    icon.icon = make_icon_image("gray")
    write_status(False)


def is_active(item) -> bool:
    return is_running()


def enroll_new_face(icon, item):
    subprocess.Popen(
        [str(SETUP_WIZARD_SCRIPT), "--add-person"],
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def open_dashboard(icon, item):
    subprocess.Popen(
        [str(DASHBOARD_SCRIPT)],
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

    subprocess.run(
        ["taskkill", "/IM", "monitor.exe", "/F"],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    write_status(False)

    if not has_any_enrolled_faces():
        subprocess.Popen(
            [str(SETUP_WIZARD_SCRIPT)],
            cwd=str(SCRIPT_DIR),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

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
    main()