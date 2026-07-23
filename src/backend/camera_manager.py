import cv2
import threading
import time
import numpy as np
from .config import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, FPS
from .hand_detector import HandDetector

class CameraManager:
    def __init__(self):
        self.detector = HandDetector()
        self.cap = None
        self.latest_frame = None
        self.latest_jpeg = None
        self.latest_gesture = "NINGUNO"
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

    def start(self) -> None:
        """Starts the background camera capture thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, name="CameraThread", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stops the background camera capture thread and releases camera."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        with self.lock:
            if self.cap and self.cap.isOpened():
                self.cap.release()
                self.cap = None

    def _run(self) -> None:
        # Initialize camera in thread
        self.cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW if os_is_windows() else cv2.CAP_ANY)
        if not self.cap or not self.cap.isOpened():
            # Fallback to general capture if DirectShow doesn't work or isn't windows
            self.cap = cv2.VideoCapture(CAMERA_INDEX)
            
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, FPS)
        else:
            print(f"Warning: Webcam with index {CAMERA_INDEX} could not be initialized.")

        frame_delay = 1.0 / FPS

        while self.running:
            start_time = time.time()
            ret = False
            frame = None

            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()

            if not ret or frame is None:
                # Create a black placeholder frame with error text
                frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
                cv2.putText(
                    frame,
                    "ERROR: Camara no disponible / ocupada",
                    (30, FRAME_HEIGHT // 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (100, 100, 255),
                    2,
                    cv2.LINE_AA
                )
                gesture = "NINGUNO"
            else:
                # Mirror the frame horizontally for standard webcam mirror effect
                frame = cv2.flip(frame, 1)
                # Process with hand detector
                try:
                    frame, gesture = self.detector.process_frame(frame)
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    gesture = "NINGUNO"

            # Compress to JPEG
            ret_encode, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            jpeg_bytes = jpeg.tobytes() if ret_encode else None

            # Thread-safe update
            with self.lock:
                self.latest_frame = frame
                self.latest_jpeg = jpeg_bytes
                self.latest_gesture = gesture

            # Wait for next frame
            elapsed = time.time() - start_time
            sleep_time = max(0.001, frame_delay - elapsed)
            time.sleep(sleep_time)

    def get_latest_jpeg(self) -> bytes:
        with self.lock:
            return self.latest_jpeg

    def get_latest_gesture(self) -> str:
        with self.lock:
            return self.latest_gesture

def os_is_windows() -> bool:
    import platform
    return platform.system().lower() == "windows"
