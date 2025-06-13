# mood_analyzer.py
import torch
import torchvision.transforms as T
from torchvision.models import resnet50

# Use PyTorch 2.x's optimizations
torch.set_float32_matmul_precision('high')  # 3x faster on modern GPUs

model = resnet50(weights='IMAGENET1K_V2')
model.eval()

def analyze_mood(frame):
    transform = T.Compose([
        T.ToPILImage(),
        T.Resize(256),
        T.CenterCrop(224),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    frame = transform(frame).unsqueeze(0)
    with torch.inference_mode():  # Faster than torch.no_grad()
        output = model(frame)
    moods = ["Happy", "Sad", "Energetic", "Calm"]
    return moods[torch.argmax(output)]