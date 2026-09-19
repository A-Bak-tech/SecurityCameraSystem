"""
Enrolls an authorized user's face for PC Guard.

Captures several frames of a face via webcam, extracts face embeddings,
averages them, and saves the result under the app's enrolled_faces
folder. Anyone enrolled this way is treated as authorized by the
live monitor.

Run directly, or launched from the tray icon's "Enroll New Face":
    python enroll_face.py
"""

import sys

import cv2
import numpy as np

from app_paths import DETECTOR_MODEL, RECOGNIZER_MODEL, ENROLLED_FACES_DIR

CAMERA_DEVICE_INDEX = 1
CAPTURES_NEEDED = 10


def main():
    print("=== PC Guard: Enroll a Face ===")
    name = input("Enter a name for this person (letters/numbers only): ").strip().lower()

    if not name or not name.isalnum():
        print("Name must be non-empty and alphanumeric (no spaces or special characters).")
        sys.exit(1)

    if not DETECTOR_MODEL.exists() or not RECOGNIZER_MODEL.exists():
        print("Model files missing — PC Guard installation may be incomplete.")
        sys.exit(1)

    output_path = ENROLLED_FACES_DIR / f"{name}.npy"

    if output_path.exists():
        response = input(f"'{name}' is already enrolled. Overwrite? (y/N): ").strip().lower()
        if response != "y":
            print("Cancelled.")
            sys.exit(0)

    cap = cv2.VideoCapture(CAMERA_DEVICE_INDEX)
    if not cap.isOpened():
        print(f"Failed to open camera device {CAMERA_DEVICE_INDEX}.")
        sys.exit(1)

    ret, frame = cap.read()
    if not ret:
        print("Failed to read a frame from the camera.")
        sys.exit(1)

    frame_height, frame_width = frame.shape[:2]

    detector = cv2.FaceDetectorYN.create(
        str(DETECTOR_MODEL), "", (frame_width, frame_height)
    )
    recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_MODEL), "")

    print(f"Enrolling '{name}'. Look at the camera. Capturing {CAPTURES_NEEDED} face samples...")
    print("Press 'q' in the camera window at any time to cancel.")

    embeddings = []

    while len(embeddings) < CAPTURES_NEEDED:
        ret, frame = cap.read()
        if not ret:
            continue

        detector.setInputSize((frame.shape[1], frame.shape[0]))
        _, faces = detector.detect(frame)

        if faces is not None and len(faces) > 0:
            face = max(faces, key=lambda f: f[2] * f[3])
            aligned_face = recognizer.alignCrop(frame, face)
            embedding = recognizer.feature(aligned_face)
            embeddings.append(embedding)

            x, y, w, h = face[:4].astype(int)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"Captured {len(embeddings)}/{CAPTURES_NEEDED}",
                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow("PC Guard - Face Enrollment", frame)
        if cv2.waitKey(200) == ord("q"):
            print("Cancelled.")
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)

    cap.release()
    cv2.destroyAllWindows()

    reference_embedding = np.mean(embeddings, axis=0)
    np.save(output_path, reference_embedding)

    print(f"Enrollment complete. '{name}' is now authorized.")
    input("Press Enter to close...")


if __name__ == "__main__":
    main()