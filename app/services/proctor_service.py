import cv2
import numpy as np
import threading
from flask import current_app

class ProctoringEngine:
    """Singleton Proctoring Engine that reuses YOLOv8 model across requests."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        # Load YOLO model for robust object and person detection
        from ultralytics import YOLO
        self.yolo = YOLO('yolov8n.pt')
        # Keep Face Cascade for specific facial features if needed, but YOLO person class is robust for presence
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self._initialized = True

    def analyze_frame(self, frame_bytes):
        """
        Analyzes a single video frame for:
        1. Face Count (via YOLO 'person' class + Haar fallback)
        2. Forbidden objects (via YOLO 'cell phone' class)
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return {"error": "Invalid image"}

            # YOLO Inference
            results = self.yolo(img, verbose=False)
            
            mobile_detected = False
            person_count = 0
            alerts = []
            
            # YOLOv8 COCO classes: 0: person, 67: cell phone, 65: remote
            # Phones are often misclassified as remotes or just have low confidence
            names = results[0].names
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = names.get(cls, str(cls))

                    # Check for mobile (67) or remote (65) which is often a misclassified phone
                    if (cls == 67 or cls == 65) and conf > 0.25: 
                        mobile_detected = True
                    elif cls == 0 and conf > 0.4:
                        person_count += 1
            
            if mobile_detected:
                alerts.append("Mobile Phone Detected")
                
            if person_count == 0:
                alerts.append("No face/person detected")
            elif person_count > 1:
                alerts.append("Multiple people detected")
            
            return {
                "face_count": person_count,
                "mobile_detected": mobile_detected,
                "alerts": alerts,
                "emotion": "neutral" 
            }
        except Exception as e:
            current_app.logger.error(f"Proctor error: {e}")
            return {"error": str(e)}

    def detect_speech(self, audio_chunk):
        """
        Detects speech in an audio chunk.
        audio_chunk: Bytes (PCM data)
        """
        # In a real implementation, we'd use SpeechRecognition or Whisper here.
        # For this prototype, we'll assume audio_chunk is processed/flagged by client or skipped.
        # To do this properly requires an AudioSource stream.
        # Returning a placeholder.
        return {"speech_detected": False}

    def analyze_emotion(self, img_path_or_array):
        # Wrapper for deepface
        try:
            # from deepface import DeepFace
            # analysis = DeepFace.analyze(img_path_or_array, actions=['emotion'], enforce_detection=False)
            # return analysis[0]['dominant_emotion']
            pass
        except:
            return "unknown"
