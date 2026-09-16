"""
Enrolls the authorized user's face for PC Guard mode.

Captures several frames of your face via webcam, extracts a face
embedding for each, averages them into one reference embedding, and
saves it to disk. Later, pc_guard's live monitor compares any detected
face against this reference to decide "authorized" vs "unknown".

Run once (or re-run to update your enrolled face):
    python enroll_face.py
"""

import sys
from pathlib import Path

import cv2
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent
DETECTOR_MODEL = MODEL_DIR / "face_detection_yunet.onnx"
RECOGNIZER_MODEL = MODEL_DIR / "face_recognition_sface.onnx"
OUTPUT_PATH = MODEL_DIR / "authorized_face.npy"

CAMERA_DEVICE_INDEX = 1  # matches config.txt's camera_device_index
CAPTURES_NEEDED = 10      # number of face samples to average together


def main():
    if not DETECTOR_MODEL.exists() or not RECOGNIZER_MODEL.exists():
        print("Model files missing. Download them first (see README/comments at top of this file).")
        sys.exit(1)

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

    print(f"Look at the camera. Capturing {CAPTURES_NEEDED} face samples...")
    print("Press 'q' at any time to cancel.")

    embeddings = []

    while len(embeddings) < CAPTURES_NEEDED:
        ret, frame = cap.read()
        if not ret:
            continue

        detector.setInputSize((frame.shape[1], frame.shape[0]))
        _, faces = detector.detect(frame)

        if faces is not None and len(faces) > 0:
            # Use the largest detected face if multiple are in frame.
            face = max(faces, key=lambda f: f[2] * f[3])
            aligned_face = recognizer.alignCrop(frame, face)
            embedding = recognizer.feature(aligned_face)
            embeddings.append(embedding)

            x, y, w, h = face[:4].astype(int)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"Captured {len(embeddings)}/{CAPTURES_NEEDED}",
                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow("Face Enrollment", frame)
        if cv2.waitKey(200) == ord("q"):
            print("Cancelled.")
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)

    cap.release()
    cv2.destroyAllWindows()

    # Average all captured embeddings into a single reference vector.
    reference_embedding = np.mean(embeddings, axis=0)
    np.save(OUTPUT_PATH, reference_embedding)

    print(f"Enrollment complete. Saved reference face to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()