import requests
import os
from dotenv import load_dotenv
load_dotenv()

API_SUBSCRIPTION_KEY = os.environ.get("SARVAM_API_KEY")
TRANSLATE_API_URL = "https://api.sarvam.ai/translate"

def translate_text(text: str, target_language_code: str, source_language_code: str) -> str:
    """
    Translate text from the source language to the target language using the translation API.
    """
    payload = {
        "input": text,
        "target_language_code": target_language_code,
        "source_language_code": source_language_code
    }

    headers = {
        "api-subscription-key": API_SUBSCRIPTION_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(TRANSLATE_API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json().get('translated_text', '')
    else:
        raise Exception(f"Translation failed: {response.text}")

# Example usage
translated_text = translate_text("Hello, world!", "hi-IN", "en-IN")
print(translated_text)