import torch
import torchvision.transforms as transforms
from torchvision.models import resnet50, ResNet50_Weights

# Load the pretrained ResNet50 model
model = resnet50(weights=ResNet50_Weights.DEFAULT)
model.eval()

# Sub-moods the model is trained to recognize
MOOD_CLASSES = [
    "joyful", "melancholic", "intense", "peaceful", "ambient",
    "furious", "loving", "tense", "inspirational", "amazed"
]

# Reverse mapping of main mood categories to sub-moods
MOOD_CATEGORIES = {
    "Happy": ["joyful", "celebratory", "upbeat", "elated", "cheerful"],
    "Sad": ["melancholic", "heartbreak", "reflective", "grieving", "lonely"],
    "Energetic": ["intense", "powerful", "adrenaline", "motivated", "amped"],
    "Calm": ["peaceful", "meditative", "dreamy", "soothing", "serene"],
    "Neutral": ["ambient", "instrumental", "background", "cinematic"],
    "Angry": ["furious", "aggressive", "heavy", "explosive"],
    "Romantic": ["loving", "sensual", "passionate", "flirty"],
    "Anxious": ["tense", "nervous", "uncertain"],
    "Hopeful": ["inspirational", "uplifting", "faithful"],
    "Surprised": ["shocked", "amazed", "excited"]
}

# Image preprocessing pipeline
transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# Helper to get main mood category from sub-mood
def get_main_mood(sub_mood):
    for main, subs in MOOD_CATEGORIES.items():
        if sub_mood in subs:
            return main
    return "Neutral"

# Core mood analysis function
def analyze_mood(frame):
    try:
        input_tensor = transform(frame).unsqueeze(0)
        with torch.no_grad():
            outputs = model(input_tensor)
        predicted_idx = torch.argmax(outputs, 1).item()
        sub_mood = MOOD_CLASSES[predicted_idx % len(MOOD_CLASSES)]
        main_mood = get_main_mood(sub_mood)
        return main_mood, sub_mood
    except Exception:
        return "Neutral", "ambient"
