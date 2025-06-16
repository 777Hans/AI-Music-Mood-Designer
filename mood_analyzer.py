import torch
import torchvision.transforms as transforms
from torchvision.models import resnet50, ResNet50_Weights
import numpy as np
import cv2
import time

# Valid moods
VALID_MOODS = ["Happy", "Sad", "Energetic", "Calm", "Neutral"]

def debug_log(message):
    """Write debug messages to log file"""
    with open("debug.log", "a") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")

class MoodAnalyzer:
    def __init__(self):
        debug_log("Initializing MoodAnalyzer...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = resnet50(weights=ResNet50_Weights.DEFAULT)
        num_ftrs = self.model.fc.in_features
        self.model.fc = torch.nn.Linear(num_ftrs, len(VALID_MOODS))
        self.model = self.model.to(self.device)
        self.model.eval()
        
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        self.mood_labels = VALID_MOODS
        debug_log("MoodAnalyzer initialized successfully")

    def preprocess_frame(self, frame):
        """Preprocess frame for model input"""
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            input_tensor = self.transform(frame_rgb).unsqueeze(0).to(self.device)
            debug_log("Frame preprocessed successfully")
            return input_tensor
        except Exception as e:
            debug_log(f"Frame preprocessing failed: {str(e)}")
            return None

    def predict_mood(self, frame):
        """Predict mood from frame"""
        try:
            input_tensor = self.preprocess_frame(frame)
            if input_tensor is None:
                debug_log("Invalid input tensor, returning Neutral")
                return "Neutral"
            
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                confidence, predicted_idx = torch.max(probabilities, 1)
                mood = self.mood_labels[predicted_idx.item()]
                
                debug_log(f"Predicted mood: {mood} (confidence: {confidence.item():.2f})")
                
                if mood not in VALID_MOODS:
                    debug_log(f"Invalid mood predicted: {mood}, returning Neutral")
                    return "Neutral"
                
                return mood
        except Exception as e:
            debug_log(f"Mood prediction failed: {str(e)}, returning Neutral")
            return "Neutral"

def analyze_mood(frame):
    """Analyze mood of a video frame"""
    try:
        analyzer = MoodAnalyzer()
        mood = analyzer.predict_mood(frame)
        debug_log(f"Final mood for frame: {mood}")
        return mood
    except Exception as e:
        debug_log(f"Analyze mood failed: {str(e)}, returning Neutral")
        return "Neutral"