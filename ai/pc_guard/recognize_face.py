"""
Compares a detected face against all enrolled authorized faces.

Used by pc_guard's live monitor: for each frame, detect a face, extract
its embedding, and check it against every enrolled person. If it's
close enough to any of them, it's authorized.
"""

from pathlib import Path

import cv2
import numpy as np

from app_paths import DETECTOR_MODEL, RECOGNIZER_MODEL, ENROLLED_FACES_DIR

MATCH_THRESHOLD = 0.363


class FaceRecognizer:
    def __init__(self):
        self.reference_embeddings = self._load_enrolled_faces()
        if not self.reference_embeddings:
            raise FileNotFoundError(
                f"No enrolled faces found in {ENROLLED_FACES_DIR}. "
                f"Run enroll_face.py <name> first."
            )

        self.detector = None
        self.recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_MODEL), "")

    def _load_enrolled_faces(self) -> dict:
        """Returns {name: embedding} for every .npy file in enrolled_faces/."""
        embeddings = {}
        if not ENROLLED_FACES_DIR.exists():
            return embeddings

        for npy_file in ENROLLED_FACES_DIR.glob("*.npy"):
            name = npy_file.stem
            embeddings[name] = np.load(npy_file)

        return embeddings

    def _ensure_detector(self, frame_width: int, frame_height: int):
        if self.detector is None:
            self.detector = cv2.FaceDetectorYN.create(
                str(DETECTOR_MODEL), "", (frame_width, frame_height)
            )
        else:
            self.detector.setInputSize((frame_width, frame_height))

    def check_frame(self, frame) -> dict:
        """
        Detects a face in frame and compares it against every enrolled
        person's reference embedding.

        Returns a dict:
            {"face_found": bool, "authorized": bool, "similarity": float,
             "matched_name": str or None}
        similarity is the best score across all enrolled people (0.0 if
        no face was found). matched_name is the enrolled person with the
        best score, or None if unauthorized/no face.
        """
        height, width = frame.shape[:2]
        self._ensure_detector(width, height)

        _, faces = self.detector.detect(frame)

        if faces is None or len(faces) == 0:
            return {"face_found": False, "authorized": False, "similarity": 0.0, "matched_name": None}

        face = max(faces, key=lambda f: f[2] * f[3])
        aligned_face = self.recognizer.alignCrop(frame, face)
        embedding = self.recognizer.feature(aligned_face)

        best_name = None
        best_similarity = 0.0

        for name, reference_embedding in self.reference_embeddings.items():
            similarity = self.recognizer.match(
                reference_embedding, embedding, cv2.FaceRecognizerSF_FR_COSINE
            )
            if similarity > best_similarity:
                best_similarity = similarity
                best_name = name

        authorized = best_similarity >= MATCH_THRESHOLD

        return {
            "face_found": True,
            "authorized": authorized,
            "similarity": float(best_similarity),
            "matched_name": best_name if authorized else None,
        }


if __name__ == "__main__":
    import sys

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Failed to open camera.")
        sys.exit(1)

    face_recognizer = FaceRecognizer()
    print(f"Enrolled: {list(face_recognizer.reference_embeddings.keys())}")
    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        result = face_recognizer.check_frame(frame)

        if result["face_found"]:
            label = result["matched_name"] if result["authorized"] else "UNKNOWN"
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