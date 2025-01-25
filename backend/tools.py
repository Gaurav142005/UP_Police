import os
from dotenv import load_dotenv
import logging
import time
from datetime import datetime
import json
import requests
import re

ERROR_LOG_FILE = "./error_logs.log"
load_dotenv('../.env')

# Create a logger for all errors
logger = logging.getLogger('my_logger')
file_Handler = logging.FileHandler(ERROR_LOG_FILE)
logger.setLevel(logging.DEBUG)  # Set the base logging level
file_Handler.setLevel(logging.ERROR)  # Set the handler logging level
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.addHandler(file_Handler)
def log_error(tool_name, error_message, additional_info=None):
    error_entry = {
        "tool" : tool_name,
        "error_message" : error_message,
        "timestamp" : datetime.now().isoformat(),
        "additional info" : additional_info or {}
    }
    logger.error(json.dumps(error_entry, indent=4))


def clean_text(text):
    text = re.sub(r'http\S+|www\S+|https\S+', '', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'"]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# @tool
def get_indian_kanoon(query: str):
    """
    Retrieves Indian LEGAL data and CASE LAWs from Indian Kanoon based on the query

    Args:
        query (str): The legal query to search for.

    Returns:
        tuple: A tuple containing the title (str), date (str), and document text (str).
    """
    # Load environment variables
    load_dotenv('../../../.env')

    INDIAN_KANOON_API_KEY = os.getenv('INDIAN_KANOON_API_KEY')

    try:
        search_url = f"https://api.indiankanoon.org/search/?formInput={query}&pagenum=0&maxcites=20"
        headers = {
            'Authorization': f'Token {INDIAN_KANOON_API_KEY}'
        }
        search_response = requests.post(search_url, headers=headers)
        search_result = search_response.json()

        # Retrieve the document ID
        doc_id = str(search_result['docs'][0]['tid'])
        doc_url = f"https://api.indiankanoon.org/doc/{doc_id}/"
        doc_response = requests.post(doc_url, headers=headers)
        doc_result = doc_response.json()

        # Extract title, date, and cleaned document text
        title = doc_result['title']
        date = doc_result['publishdate']
        doc = clean_text(doc_result['doc'])
        output_folder = "temp_rag_space"
        print(os.getcwd())
        os.makedirs(output_folder, exist_ok=True)        
        # Generate filename based on URL and timestamp
        filename = f"legal{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(output_folder, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(doc)

        delay = 2
        time.sleep(delay)
        source = 'Indian Kanoon'
        # response_query_document = query_documents.invoke({"prompt":query,"source": source}) 
        # if response_query_document == "This tool is not working right now. DO NOT CALL THIS TOOL AGAIN!":
        #     return doc
        # else:
        #     return response_query_document

    except Exception as e:
        log_error(
            tool_name="get_Indian_kanoon",
            error_message=str(e),
            additional_info={"query": query}
        )
        return "This tool is not working right now. DO NOT CALL THIS TOOL AGAIN!"


# get_indian_kanoon("Uttar Pradesh police corruption")