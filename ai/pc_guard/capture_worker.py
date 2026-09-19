"""
PC Guard capture worker: handles all camera/cv2 work as its own
process, since cv2 cannot safely share a process with tkinter or
pystray on this machine (confirmed DLL-level crash otherwise).

Modes (first command-line argument):
    select_camera          - lets the user cycle through camera
                              indices and confirm one; writes the
                              chosen index to result.json
    enroll <index> <name>  - captures face samples from the given
                              camera index and saves the enrollment;
                              writes success/failure to result.json

Always writes its result as JSON to app_paths.APP_DATA_DIR / "worker_result.json"
before exiting, so the calling process (setup_wizard.py) can read it
after this process closes.
"""

import sys
print("Step 1: sys imported", flush=True)

import json
print("Step 2: json imported", flush=True)

import cv2
print("Step 3: cv2 imported", flush=True)

import numpy as np
print("Step 4: numpy imported", flush=True)

from app_paths import DETECTOR_MODEL, RECOGNIZER_MODEL, ENROLLED_FACES_DIR, APP_DATA_DIR
print("Step 5: app_paths imported", flush=True)

RESULT_PATH = APP_DATA_DIR / "worker_result.json"
CAPTURES_NEEDED = 10


def write_result(result: dict):
    with open(RESULT_PATH, "w") as f:
        json.dump(result, f)


def select_camera_mode():
    index = 0
    cap = None

    def open_index(i):
        nonlocal cap
        if cap is not None:
            cap.release()
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) #DSHOW backend often fails faster on invalid indices
        print(f"Step 7: VideoCapture({i}) opened = {cap.isOpened()}", flush=True)
        return cap.isOpened()

    is_open = open_index(index)
    print("Step 8: first camerea check done", flush=True)

    print("Camera selection started.", flush=True)

    while True:
        display = None
        if is_open:
            ret, frame = cap.read()
            if ret:
                display = frame

        if display is None:
            display = np.zeros((300, 400, 3), dtype=np.uint8)
            cv2.putText(display, f"Camera {index}: not available",
                        (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            cv2.putText(display, f"Camera {index}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            cv2.putText(display, "A: previous camera   D: next camera   SPACE: use this camera   ESC: cancel",
                    (10, display.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("PC Guard - Choose Camera", display)
        key = cv2.waitKey(15) & 0xFF
        if key != 255: # 255 means "no key pressed this frame"
            print(f"Key detected: {key}", flush=True)

        if key == 27:  # ESC
            write_result({"success": False, "reason": "cancelled"})
            break
        elif key == 32:  # SPACE
            if is_open:
                write_result({"success": True, "camera_index": index})
                break
        elif key == ord('a') or key == ord('A'):
            index = max(0, index - 1)
            is_open = open_index(index)
        elif key == ord('d') or key == ord('D'):
            index += 1
            is_open = open_index(index)

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()


def enroll_mode(camera_index: int, name: str):
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        write_result({"success": False, "reason": "camera_unavailable"})
        return

    ret, frame = cap.read()
    if not ret:
        write_result({"success": False, "reason": "camera_read_failed"})
        cap.release()
        return

    h, w = frame.shape[:2]
    detector = cv2.FaceDetectorYN.create(str(DETECTOR_MODEL), "", (w, h))
    recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_MODEL), "")

    embeddings = []
    cancelled = False

    print("Enrollment capture started.", flush=True)

    while len(embeddings) < CAPTURES_NEEDED:
        ret, frame = cap.read()
        if not ret:
            continue

        detector.setInputSize((frame.shape[1], frame.shape[0]))
        _, faces = detector.detect(frame)

        if faces is not None and len(faces) > 0:
            face = max(faces, key=lambda f: f[2] * f[3])
            aligned = recognizer.alignCrop(frame, face)
            embedding = recognizer.feature(aligned)
            embeddings.append(embedding)

            x, y, fw, fh = face[:4].astype(int)
            cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)

        cv2.putText(frame, f"Hold still - capturing {len(embeddings)}/{CAPTURES_NEEDED}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "Press ESC to cancel", (10, frame.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("PC Guard - Enrolling Face", frame)
        if cv2.waitKey(150) & 0xFF == 27:
            cancelled = True
            break

    cap.release()
    cv2.destroyAllWindows()

    if cancelled:
        write_result({"success": False, "reason": "cancelled"})
        return

    reference_embedding = np.mean(embeddings, axis=0)
    output_path = ENROLLED_FACES_DIR / f"{name}.npy"
    np.save(output_path, reference_embedding)

    write_result({"success": True, "name": name})


def main():
    if len(sys.argv) < 2:
        write_result({"success": False, "reason": "no_mode_specified"})
        return

    mode = sys.argv[1]

    if mode == "select_camera":
        select_camera_mode()
    elif mode == "enroll":
        if len(sys.argv) < 4:
            write_result({"success": False, "reason": "missing_arguments"})
            return
        camera_index = int(sys.argv[2])
        name = sys.argv[3]
        enroll_mode(camera_index, name)
    else:
        write_result({"success": False, "reason": f"unknown_mode:{mode}"})


if __name__ == "__main__":
    main()