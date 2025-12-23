import os
from model import Chatbot
import json

# Load queries
with open("testing_queries.json", "r") as f:
    queries = json.load(f)
queries = [q for i in list(queries.values()) for q in i]

api_keys = [
# Add your api keys
]
BATCH_SIZE = 1

for i, query in enumerate(queries):
    
    # Check if we need to switch keys (Start of loop OR every 5th query)
    if i % BATCH_SIZE == 0:
        key_index = (i // BATCH_SIZE) % len(api_keys)
        current_key = api_keys[key_index]
        
        print(f"\n🔄 Switching to API Key Index {key_index}...")
        
        # A. Update the Environment Variable
        os.environ["GOOGLE_API_KEY"] = current_key
        
        # B. Re-initialize Chatbot 
        # (This now triggers the new self.client = genai.Client(...) line in model.py)
        chatbot = Chatbot()

    # 4. Run the query
    try:
        print(f"Query {i+1}: {query}")
        response = chatbot.chatbot(query, language='english')
        print("Response received.")
        # print(response) # Uncomment to see full response
    except Exception as e:
        print(f"❌ Error on Query {i+1}: {e}")