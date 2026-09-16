"""
Headless live test: captures frames continuously, checks each against
the enrolled face, prints results to console, and saves an annotated
snapshot periodically so you can visually confirm without cv2.imshow.
"""

import time
import cv2
from recognize_face import FaceRecognizer

def main():
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Failed to open camera.")
        return

    recognizer = FaceRecognizer()
    print("Running. Press Ctrl+C to stop.")

    last_save = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            result = recognizer.check_frame(frame)
            print(result, flush=True)

            now = time.time()
            if now - last_save > 2:
                cv2.imwrite("live_test_frame.jpg", frame)
                last_save = now

            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()

if __name__ == "__main__":
    main()