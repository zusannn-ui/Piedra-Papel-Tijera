import cv2
import mediapipe as mp
from typing import Tuple

class HandDetector:
    def __init__(self, min_detection_confidence: float = 0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

    def process_frame(self, frame) -> Tuple[any, str]:
        """
        Processes a BGR OpenCV frame.
        Draws landmarks on the frame if a hand is detected.
        Returns the annotated frame and the detected gesture string: "PIEDRA", "PAPEL", "TIJERA", or "NINGUNO".
        """
        # Convert BGR frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = self.hands.process(rgb_frame)
        
        gesture = "NINGUNO"
        
        if results.multi_hand_landmarks:
            # Draw landmarks
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
            
            # Extract first detected hand
            hand_landmarks = results.multi_hand_landmarks[0]
            landmarks = hand_landmarks.landmark
            
            # Ensure we have all 21 landmarks
            if len(landmarks) >= 21:
                # Check status of the 4 long fingers
                # Coordinate y: 0 is top, 1 is bottom. 
                # So tip.y < pip.y means tip is higher (closer to top of screen) -> open.
                index_open = landmarks[8].y < landmarks[6].y
                middle_open = landmarks[12].y < landmarks[10].y
                ring_open = landmarks[16].y < landmarks[14].y
                pinky_open = landmarks[20].y < landmarks[18].y
                
                # Classify gesture based on rules:
                # - PAPEL: all 4 open
                # - PIEDRA: all 4 closed
                # - TIJERA: index & middle open, ring & pinky closed
                if index_open and middle_open and ring_open and pinky_open:
                    gesture = "PAPEL"
                elif (not index_open) and (not middle_open) and (not ring_open) and (not pinky_open):
                    gesture = "PIEDRA"
                elif index_open and middle_open and (not ring_open) and (not pinky_open):
                    gesture = "TIJERA"
                else:
                    gesture = "NINGUNO"
        
        # Annotate gesture text on the frame
        cv2.putText(
            frame,
            f"GESTO: {gesture}",
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 0, 127) if gesture != "NINGUNO" else (128, 128, 128),
            2,
            cv2.LINE_AA
        )
        
        return frame, gesture
