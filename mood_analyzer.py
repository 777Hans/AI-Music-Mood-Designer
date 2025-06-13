import torch
import torchvision.transforms as T
from torchvision.models import resnet50
import cv2
import numpy as np

# Initialize model with optimizations
torch.set_float32_matmul_precision('high')  # Better performance on modern hardware

# Load pre-trained ResNet50
model = resnet50(weights='IMAGENET1K_V2')
model.eval()

# Define mood categories (aligned with ImageNet classes)
MOOD_MAPPING = {
    # Happy (smiling faces, celebrations)
    "Happy": [32, 33, 34, 35, 36],  # Goldfish, jellyfish, etc.
    # Sad (rain, abandoned places)
    "Sad": [963, 964, 965],  # War memorials, ruins
    # Energetic (sports, dancing)
    "Energetic": [400, 401, 402, 873],  # Soccer, tennis, etc.
    # Calm (nature scenes)
    "Calm": [970, 971, 972, 973]  # Lakes, mountains
}

# Image preprocessing pipeline
transform = T.Compose([
    T.ToPILImage(),
    T.Resize(256),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def analyze_mood(frame):
    """
    Analyzes mood from a video frame using deep learning.
    
    Args:
        frame (numpy.ndarray): Input frame in BGR format
        
    Returns:
        str: Detected mood ("Happy", "Sad", "Energetic", "Calm", or "Neutral")
    """
    try:
        # Validate input frame
        if frame is None or frame.size == 0:
            return "Neutral"
            
        # Convert BGR to RGB and check dimensions
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            return "Neutral"
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Apply transformations
        input_tensor = transform(rgb_frame).unsqueeze(0)
        
        # Model prediction
        with torch.inference_mode():
            outputs = model(input_tensor)
            _, preds = torch.max(outputs, 1)
            predicted_class = preds.item()
            
        # Map ImageNet class to mood
        for mood, classes in MOOD_MAPPING.items():
            if predicted_class in classes:
                return mood
                
        # Fallback for unclassified images
        probs = torch.nn.functional.softmax(outputs, dim=1)[0]
        if probs[predicted_class] < 0.5:  # Low confidence
            return "Neutral"
            
        # Default to first mood if no mapping found
        return list(MOOD_MAPPING.keys())[0]
        
    except Exception as e:
        print(f"[Error] Mood analysis failed: {str(e)}")
        return "Neutral"

# Test function for debugging
def test_mood_analyzer():
    """Test the mood analyzer with sample images"""
    test_images = {
        "happy": np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8),
        "sad": np.random.randint(0, 100, (224, 224, 3), dtype=np.uint8)
    }
    
    for name, img in test_images.items():
        mood = analyze_mood(img)
        print(f"Test '{name}': {mood}")

if __name__ == "__main__":
    test_mood_analyzer()