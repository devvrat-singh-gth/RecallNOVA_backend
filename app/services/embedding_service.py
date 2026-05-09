import requests
from app.config import HF_API_KEY

API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"

headers = {
    "Authorization": f"Bearer {HF_API_KEY}"
}

def get_embedding(text: str):
    response = requests.post(API_URL, headers=headers, json={"inputs": text})
    return response.json()[0]