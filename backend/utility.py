import requests
import os
from dotenv import load_dotenv
import subprocess
load_dotenv()

def convert_to_html(content):
    # Save content to a markdown file
    with open('Response.md', 'w') as file:
        file.write(content)

    try:
        # Execute the command
        result = subprocess.run(
            ['grip', 'Response.md', '--export', 'Response.html'],  # Command and arguments as a list
            check=True,                                   # Raise an exception if the command fails
            capture_output=True,                          # Capture the command's output
            text=True                                     # Ensure output is in text format, not bytes
        )
        print("Command executed successfully!")
        print(result.stdout)  # Print any output
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e.stderr}")
    except FileNotFoundError:
        print("The 'grip' command was not found. Ensure it is installed and available in your PATH.")



API_SUBSCRIPTION_KEY = os.environ.get("SARVAM_API_KEY")
TRANSLATE_API_URL = "https://api.sarvam.ai/translate"

def translate_text(target_language_code: str, source_language_code: str, text: str) -> str:
    """
    Translate text from the source language to the target language using the translation API.
    """
    if(text == ''):
        text = "Hello Uttar Pradesh Police! How may I help you today"
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