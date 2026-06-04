from telethon import TelegramClient, events
import os
import requests
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# ================= TELEGRAM =================
api_id = 00000000 #API id of your telegram account
api_hash = "" #API hash of your telegram account

BOT_USERNAME = "" #the name of your bot

client = TelegramClient("session", api_id, api_hash)

# ================= CONFIG =================
MODEL_PATH = r"" #path where your model is saved

SAVE_DIR = r"" #path of the folder where the images are to be saved
SAVE_PATH = os.path.join(SAVE_DIR, "latest.jpg")

ESP32_IP = "10.159.103.58" #PASTE the new ESP32 ip address RIGHT HERE!!!

IMG_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

classes = ['damaged', 'old', 'ripe', 'unripe']

os.makedirs(SAVE_DIR, exist_ok=True)

# ================= TRANSFORM =================
transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485, 0.456, 0.406],
        [0.229, 0.224, 0.225]
    )
])

# ================= MODEL =================
def load_model():

    model = models.efficientnet_v2_s(weights=None)

    num_features = model.classifier[1].in_features

    model.classifier[1] = nn.Linear(
        num_features,
        len(classes)
    )

    checkpoint = torch.load(
        MODEL_PATH,
        map_location=DEVICE
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model.to(DEVICE)
    model.eval()

    return model

model = load_model()

# ================= PREDICT =================
def predict(image_path):

    image = Image.open(image_path).convert("RGB")

    image = transform(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():

        outputs = model(image)

        probs = torch.softmax(outputs, dim=1)

        idx = torch.argmax(probs, dim=1).item()

    label = classes[idx]

    confidence = float(probs[0][idx].item())

    return label, confidence

# ================= TELEGRAM LISTENER =================
@client.on(events.NewMessage)
async def handler(event):

    try:
        # ================= PHOTO DETECT =================
        if event.photo:

            print("\nBot image detected")

            # ================= DOWNLOAD =================
            await event.download_media(file=SAVE_PATH)

            print("Image saved:", SAVE_PATH)

            # ================= PREDICTION =================
            try:

                label, conf = predict(SAVE_PATH)

                print(f"Prediction: {label}")
                print(f"Confidence: {conf:.3f}")

                # ================= SEND TO ESP32 =================
                try:

                    requests.get(
                        f"http://{ESP32_IP}/data",
                        params={
                            "label": label,
                            "conf": round(conf, 3)
                        },
                        timeout=5
                    )

                    print("Sent to ESP32")

                except Exception as e:
                    print("ESP32 send error:", e)

            except Exception as e:
                print("Prediction error:", e)

    except Exception as e:
        print("Handler error:", e)

# ================= START =================
print("Listening for bot photos...")

client.start()

client.run_until_disconnected()