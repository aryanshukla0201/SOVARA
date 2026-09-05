import base64
import requests


IMAGE_PATH = r"C:\Users\ARYAN\OneDrive\Desktop\AI\GEN-AI\SOVARA\data\test\Screenshot 2026-08-29 002329.png"
MODEL = "gemma3:4b-it-qat"
OLLAMA_URL = "http://localhost:11434/api/generate"


with open(IMAGE_PATH, "rb") as image_file:
    image_base64 = base64.b64encode(image_file.read()).decode("utf-8")


payload = {
    "model": MODEL,
    "prompt": (
        "Analyze this image carefully. "
        "Describe what you see, including important objects, "
        "text, visual relationships, and anything relevant "
        "for further analysis."
    ),
    "images": [image_base64],
    "stream": False,
}


response = requests.post(
    OLLAMA_URL,
    json=payload,
    timeout=120,
)


print("HTTP status:", response.status_code)

response.raise_for_status()

result = response.json()

print("\nGemma response:\n")
print(result["response"])
