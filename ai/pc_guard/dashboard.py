"""
PC Guard dashboard: status, enrolled people, settings, and recent
activity — all in one window. Pure tkinter, no cv2 import (camera
work is delegated to setup_wizard.py/capture_worker.py subprocesses).
"""

import subprocess
import sqlite3
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from app_paths import (
    ENROLLED_FACES_DIR, DB_PATH, load_config, save_config, read_status,
)

if getattr(sys, "frozen", False):
    SCRIPT_DIR = Path(sys.executable).resolve().parent
else:
    SCRIPT_DIR = Path(__file__).resolve().parent


class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PC Guard Dashboard")
        self.geometry("520x480")

        self.config_data = load_config()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.status_tab = ttk.Frame(notebook)
        self.people_tab = ttk.Frame(notebook)
        self.settings_tab = ttk.Frame(notebook)
        self.activity_tab = ttk.Frame(notebook)

        notebook.add(self.status_tab, text="Status")
        notebook.add(self.people_tab, text="Enrolled People")
        notebook.add(self.settings_tab, text="Settings")
        notebook.add(self.activity_tab, text="Activity")

        self.build_status_tab()
        self.build_people_tab()
        self.build_settings_tab()
        self.build_activity_tab()

    def build_status_tab(self):
        running = read_status()
        color = "#2a9d3f" if running else "#888888"
        text = "Protected" if running else "Paused"

        tk.Label(self.status_tab, text=text, font=("Segoe UI", 20, "bold"), fg=color).pack(pady=30)
        ttk.Label(
            self.status_tab, wraplength=400, justify="center",
            text="Start or stop protection from the PC Guard tray icon "
                 "(right-click it in your system tray).",
        ).pack(pady=10)
        ttk.Button(self.status_tab, text="Refresh", command=self.refresh_status).pack(pady=10)

    def refresh_status(self):
        for widget in self.status_tab.winfo_children():
            widget.destroy()
        self.build_status_tab()

    def build_people_tab(self):
        for widget in self.people_tab.winfo_children():
            widget.destroy()

        ttk.Label(self.people_tab, text="Authorized Users", font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))

        list_frame = ttk.Frame(self.people_tab)
        list_frame.pack(fill="both", expand=True, padx=10)

        people = sorted(p.stem for p in ENROLLED_FACES_DIR.glob("*.npy"))

        if not people:
            ttk.Label(list_frame, text="No one enrolled yet.").pack(pady=20)
        else:
            for name in people:
                row = ttk.Frame(list_frame)
                row.pack(fill="x", pady=3)
                ttk.Label(row, text=name.title(), font=("Segoe UI", 11)).pack(side="left")
                ttk.Button(row, text="Remove", command=lambda n=name: self.remove_person(n)).pack(side="right")

        ttk.Button(self.people_tab, text="+ Add Person", command=self.add_person).pack(pady=15)

    def remove_person(self, name: str):
        if messagebox.askyesno("Remove Person", f"Remove '{name.title()}' as an authorized user?"):
            (ENROLLED_FACES_DIR / f"{name}.npy").unlink(missing_ok=True)
            self.build_people_tab()

    def add_person(self):
        subprocess.run(
            [str(SCRIPT_DIR / "setup_wizard.exe"), "--add-person"],
            cwd=str(SCRIPT_DIR),
        )
        self.build_people_tab()

    def build_settings_tab(self):
        frame = self.settings_tab

        ttk.Label(frame, text="Check-in sensitivity", font=("Segoe UI", 11, "bold")).pack(pady=(15, 5), anchor="w", padx=15)
        ttk.Label(
            frame, wraplength=440, justify="left",
            text="How often PC Guard re-checks who's using the computer during "
                 "continuous activity. Lower = faster detection, more frequent camera checks.",
        ).pack(padx=15, anchor="w")

        self.periodic_var = tk.DoubleVar(value=self.config_data.get("periodic_recheck_seconds", 8.0))
        scale = ttk.Scale(frame, from_=3, to=60, variable=self.periodic_var, orient="horizontal", length=400)
        scale.pack(padx=15, pady=10)
        self.periodic_label = ttk.Label(frame, text=f"{self.periodic_var.get():.0f} seconds")
        self.periodic_label.pack()
        scale.configure(command=lambda v: self.periodic_label.config(text=f"{float(v):.0f} seconds"))

        self.sound_var = tk.BooleanVar(value=self.config_data.get("sound_enabled", True))
        ttk.Checkbutton(frame, text="Play a sound when an alert triggers", variable=self.sound_var).pack(
            pady=20, anchor="w", padx=15
        )

        ttk.Button(frame, text="Save Settings", command=self.save_settings).pack(pady=20)

    def save_settings(self):
        self.config_data["periodic_recheck_seconds"] = self.periodic_var.get()
        self.config_data["sound_enabled"] = self.sound_var.get()
        save_config(self.config_data)
        messagebox.showinfo("Saved", "Settings saved. Restart protection from the tray icon for changes to take effect.")

    def build_activity_tab(self):
        columns = ("time", "type")
        tree = ttk.Treeview(self.activity_tab, columns=columns, show="headings", height=15)
        tree.heading("time", text="Time")
        tree.heading("type", text="Event")
        tree.column("time", width=160)
        tree.column("type", width=280)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        if DB_PATH.exists():
            conn = sqlite3.connect(DB_PATH)
            try:
                rows = conn.execute(
                    "SELECT created_at, event_type FROM events ORDER BY id DESC LIMIT 50"
                ).fetchall()
                for created_at, event_type in rows:
                    tree.insert("", "end", values=(created_at, event_type))
            finally:
                conn.close()


def main():
    app = Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()