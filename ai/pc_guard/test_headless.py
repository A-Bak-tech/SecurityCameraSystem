"""
Headless test of FaceRecognizer — no cv2.imshow, just captures one frame
and prints the result. Used to isolate whether the GUI window is the
source of a crash.
"""

import cv2
from recognize_face import FaceRecognizer

def main():
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Failed to open camera.")
        return

    print("Camera opened. Capturing one frame...")
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Failed to read frame.")
        return

    print("Frame captured. Running face recognition...")
    recognizer = FaceRecognizer()
    result = recognizer.check_frame(frame)
    print("Result:", result)

if __name__ == "__main__":
    main()