from transformers import pipeline
import logging

logger = logging.getLogger(__name__)

class EmotionDetector:
    def __init__(self):
        self.model = None
        self.load_model()

    def load_model(self):
        try:
            # Use a smaller model for faster inference
            self.model = pipeline(
                "text-classification", 
                model="j-hartmann/emotion-english-distilroberta-base",
                top_k=1
            )
            logger.info("Emotion detector loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading emotion detector: {e}")
            self.model = None

    def detect_emotion(self, text):
        if not text.strip() or self.model is None:
            return "neutral"
        try:
            result = self.model(text)[0][0]
            return result['label'].lower()
        except Exception as e:
            logger.error(f"Emotion detection error: {e}")
            return "neutral"