' Launches monitor.py invisibly (no console window) using the same
' Python interpreter and working directory as manual runs.
Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = "C:\SecurityCameraSystem\ai\pc_guard"
objShell.Run "pythonw.exe monitor.py", 0, False