"""
PC Guard first-run setup wizard. Pure tkinter — never imports cv2 or
PIL directly, since those crash when combined with tkinter in this
environment. Camera/face work is delegated to capture_worker.py,
launched as a separate process for each step.
"""

import sys
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from app_paths import APP_DATA_DIR, load_config, save_config, ENROLLED_FACES_DIR

if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent
WORKER_SCRIPT = SCRIPT_DIR / "capture_worker.exe"
RESULT_PATH = APP_DATA_DIR / "worker_result.json"


def run_worker(*args) -> dict:
    """Launches capture_worker.py with the given args, waits for it to
    finish, and returns its JSON result."""
    if RESULT_PATH.exists():
        RESULT_PATH.unlink()

    subprocess.run([str(WORKER_SCRIPT), *args], cwd=str(SCRIPT_DIR))

    if not RESULT_PATH.exists():
        return {"success": False, "reason": "worker_produced_no_result"}

    with open(RESULT_PATH, "r") as f:
        return json.load(f)


class SetupWizard(tk.Tk):
    def __init__(self, add_person_mode: bool):
        super().__init__()
        self.title("PC Guard Setup")
        self.geometry("480x360")
        self.resizable(False, False)

        self.add_person_mode = add_person_mode
        self.config_data = load_config()
        self.enroll_name = None

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        if add_person_mode:
            self.show_name_step()
        else:
            self.show_welcome_step()

    def clear_frame(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # --- Step 1: Welcome -----------------------------------------------

    def show_welcome_step(self):
        self.clear_frame()
        ttk.Label(self.container, text="Welcome to PC Guard", font=("Segoe UI", 16, "bold")).pack(pady=(30, 10))
        ttk.Label(
            self.container, wraplength=400, justify="center",
            text=(
                "PC Guard watches for unauthorized use of your computer while "
                "you're away, and locks your PC if it doesn't recognize who's using it.\n\n"
                "Let's get you set up — this takes about a minute."
            ),
        ).pack(pady=10, padx=30)
        ttk.Button(self.container, text="Get Started", command=self.show_camera_step).pack(pady=30)

    # --- Step 2: Camera selection ---------------------------------------

    def show_camera_step(self):
        self.clear_frame()
        ttk.Label(self.container, text="Choose Your Camera", font=("Segoe UI", 14, "bold")).pack(pady=(30, 10))
        ttk.Label(
            self.container, wraplength=400, justify="center",
            text="A window will open showing your camera. Use the LEFT/RIGHT "
                 "arrow keys to try different cameras, then press SPACE when "
                 "you see the right one.",
        ).pack(pady=10, padx=30)
        ttk.Button(self.container, text="Open Camera Selector", command=self.launch_camera_selector).pack(pady=20)

    def launch_camera_selector(self):
        result = run_worker("select_camera")
        if result.get("success"):
            self.config_data["camera_device_index"] = result["camera_index"]
            save_config(self.config_data)
            self.show_name_step()
        else:
            messagebox.showwarning(
                "No Camera Selected",
                "No camera was selected. You can try again.",
            )

    # --- Step 3: Name entry ----------------------------------------------

    def show_name_step(self):
        self.clear_frame()
        ttk.Label(self.container, text="Who Are We Enrolling?", font=("Segoe UI", 14, "bold")).pack(pady=(30, 10))
        ttk.Label(
            self.container, wraplength=400, justify="center",
            text="Enter a name for this person. They'll be recognized as an authorized user.",
        ).pack(pady=10)

        self.name_entry = ttk.Entry(self.container, width=30, font=("Segoe UI", 12))
        self.name_entry.pack(pady=10)
        self.name_entry.focus()

        ttk.Button(self.container, text="Continue", command=self.confirm_name).pack(pady=20)

    def confirm_name(self):
        name = self.name_entry.get().strip().lower()
        if not name or not name.isalnum():
            messagebox.showwarning("Invalid Name", "Please use only letters and numbers.")
            return

        if (ENROLLED_FACES_DIR / f"{name}.npy").exists():
            if not messagebox.askyesno("Already Enrolled", f"'{name}' is already enrolled. Overwrite?"):
                return

        self.enroll_name = name
        self.show_capture_step()

    # --- Step 4: Face capture ---------------------------------------------

    def show_capture_step(self):
        self.clear_frame()
        ttk.Label(self.container, text=f"Ready to Capture, {self.enroll_name.title()}",
                  font=("Segoe UI", 14, "bold")).pack(pady=(30, 10))
        ttk.Label(
            self.container, wraplength=400, justify="center",
            text="A window will open. Look at the camera and hold still while "
                 "it captures a few samples of your face.",
        ).pack(pady=10, padx=30)
        ttk.Button(self.container, text="Start Capturing", command=self.launch_enrollment).pack(pady=20)

    def launch_enrollment(self):
        camera_index = self.config_data.get("camera_device_index", 0)
        result = run_worker("enroll", str(camera_index), self.enroll_name)

        if result.get("success"):
            self.show_done_step()
        else:
            reason = result.get("reason", "unknown")
            messagebox.showerror("Enrollment Failed", f"Something went wrong ({reason}). Let's try again.")
            self.show_capture_step()

    # --- Step 5: Done ------------------------------------------------------

    def show_done_step(self):
        self.clear_frame()
        ttk.Label(self.container, text="All Set!", font=("Segoe UI", 16, "bold")).pack(pady=(50, 10))
        ttk.Label(
            self.container, wraplength=400, justify="center",
            text=f"'{self.enroll_name.title()}' is now an authorized user.\n\n"
                 "PC Guard will run in your system tray and keep watch whenever you step away.",
        ).pack(pady=10, padx=30)
        ttk.Button(self.container, text="Finish", command=self.destroy).pack(pady=30)


def main():
    add_person_mode = "--add-person" in sys.argv
    app = SetupWizard(add_person_mode=add_person_mode)
    app.mainloop()


if __name__ == "__main__":
    main()