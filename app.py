from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from convert import convert_to_html
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from werkzeug.utils import secure_filename
from Chatbot import chatbot

app = Flask(__name__)
CORS(app)  

@app.route('/query', methods=['POST'])
def handle_query():
    # Parse the JSON requestx
    data = request.json
    query = data.get('query', '')

    # Log or process the received query
    # response = chatbot(query)
    response = {"message":'''
                File "/Users/gauravrampuria/Desktop/UP Police UI/UI-3GPP/UPP/lib/python3.11/site-packages/groq/_base_client.py", line 1061, in _request
    raise self._make_status_error_from_response(err.response) from None
groq.RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01j9ak92jve0s9v46tr7044xfg` service tier `on_demand` on : Limit 100000, Used 99101, Requested 1484. Please try again in 8m25.107s. Visit https://console.groq.com/docs/rate-limits for more information.', 'type': '', 'code': 'rate_limit_exceeded'}}
During task with name 'retrieve' and id 'cfb21694-46d7-b9b2-99af-eeb985d0bcbe'
                '''}
    # print(response)
    return response,200

@app.route('/convert', methods=['POST'])
def convert_to_pdf():
    data = request.get_json()
    markdown_content = data.get('content', '')
    print(f"Received markdown content: {markdown_content}")
    markdown_content = str(markdown_content)
    convert_to_html(markdown_content)
    if not os.path.exists("pathway.html"):
        return {"error": "Failed to generate PDF"}, 500

    return {"message": "PDF generated successfully"}

@app.route('/download-pdf', methods=['GET'])
def download_pdf():
    output_file = 'pathway.html'

    # Check if the PDF exists
    if not os.path.exists(output_file):
        return {"error": "PDF not found"}, 404

    return send_file(output_file, as_attachment=True, download_name='pathway.html', mimetype='text/html')


app = Flask(__name__)

# Google Drive API settings
SERVICE_ACCOUNT_FILE = "apikey.json"  # Replace with your service account file
FOLDER_ID = "1dx3fQhtNuC_EOSVnV5Rio5zoogRKzkbf"  # Replace with your Google Drive folder ID

# Authenticate using the service account
def authenticate():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=credentials)

# Function to upload a file to Google Drive
def upload_to_drive(file_path, file_name):
    drive_service = authenticate()

    file_metadata = {
        "name": file_name,
        "parents": [FOLDER_ID],  # Upload to the specified folder
    }
    
    # Create a MediaFileUpload object for the file to be uploaded
    media = MediaFileUpload(file_path, mimetype="application/pdf", resumable=True)

    try:
        upload_response = drive_service.files().create(
            body=file_metadata, media_body=media, fields="id, webViewLink"
        ).execute()

        return upload_response

    except Exception as e:
        raise Exception(f"Error uploading file: {str(e)}")
    
@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Secure filename and save temporarily
    filename = secure_filename(file.filename)
    temp_path = os.path.join("uploads", filename)
    os.makedirs("uploads", exist_ok=True)
    file.save(temp_path)

    try:
        # Upload to Google Drive
        drive_response = upload_to_drive(temp_path, filename)
        os.remove(temp_path)  # Remove file after upload
        return jsonify({"file_id": drive_response["id"], "webViewLink": drive_response["webViewLink"]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080, debug=True)  # Run Flask server on port 8080