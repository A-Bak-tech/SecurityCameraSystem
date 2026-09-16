"""
Compares a detected face against the enrolled authorized face.

Used by pc_guard's live monitor: for each frame, detect a face, extract
its embedding, and check whether it matches the enrolled reference
closely enough to count as "authorized."
"""

from pathlib import Path

import cv2
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent
DETECTOR_MODEL = MODEL_DIR / "face_detection_yunet.onnx"
RECOGNIZER_MODEL = MODEL_DIR / "face_recognition_sface.onnx"
REFERENCE_PATH = MODEL_DIR / "authorized_face.npy"

# SFace's cosine similarity threshold for "same person." Values above
# this count as a match; below counts as an unknown/different face.
# 0.363 is OpenCV's documented default threshold for SFace.
MATCH_THRESHOLD = 0.363


class FaceRecognizer:
    def __init__(self):
        if not REFERENCE_PATH.exists():
            raise FileNotFoundError(
                f"No enrolled face found at {REFERENCE_PATH}. Run enroll_face.py first."
            )

        self.reference_embedding = np.load(REFERENCE_PATH)
        self.detector = None  # created lazily once frame size is known
        self.recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_MODEL), "")

    def _ensure_detector(self, frame_width: int, frame_height: int):
        if self.detector is None:
            self.detector = cv2.FaceDetectorYN.create(
                str(DETECTOR_MODEL), "", (frame_width, frame_height)
            )
        else:
            self.detector.setInputSize((frame_width, frame_height))

    def check_frame(self, frame) -> dict:
        """
        Detects a face in frame and compares it to the enrolled reference.

        Returns a dict:
            {"face_found": bool, "authorized": bool, "similarity": float}
        similarity is 0.0 if no face was found.
        """
        height, width = frame.shape[:2]
        self._ensure_detector(width, height)

        _, faces = self.detector.detect(frame)

        if faces is None or len(faces) == 0:
            return {"face_found": False, "authorized": False, "similarity": 0.0}

        # Use the largest detected face if multiple are in frame.
        face = max(faces, key=lambda f: f[2] * f[3])
        aligned_face = self.recognizer.alignCrop(frame, face)
        embedding = self.recognizer.feature(aligned_face)

        similarity = self.recognizer.match(
            self.reference_embedding, embedding, cv2.FaceRecognizerSF_FR_COSINE
        )

        authorized = similarity >= MATCH_THRESHOLD

        return {"face_found": True, "authorized": authorized, "similarity": float(similarity)}


if __name__ == "__main__":
    # Quick manual test: shows live camera feed, prints match status per frame.
    import sys

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Failed to open camera.")
        sys.exit(1)

    face_recognizer = FaceRecognizer()

    print("Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        result = face_recognizer.check_frame(frame)

        if result["face_found"]:
            label = "AUTHORIZED" if result["authorized"] else "UNKNOWN"
            color = (0, 255, 0) if result["authorized"] else (0, 0, 255)
            text = f"{label} ({result['similarity']:.3f})"
            cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        else:
            cv2.putText(frame, "No face detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.imshow("Face Recognition Test", frame)
        if cv2.waitKey(1) == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()