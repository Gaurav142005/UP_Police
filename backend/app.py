from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from werkzeug.utils import secure_filename
from model import Chatbot
from utility import translate_text, convert_to_html

app = Flask(__name__)
CORS(app)  
bot = Chatbot()

@app.route('/query', methods=['POST'])
def handle_query():
    # Parse the JSON requestx
    data = request.json
    query = data.get('query', '')
    print(query)
    language = data.get('lang', '')
    print(language)
    response = bot.chatbot(query, language)   
    print(response)
    # Log or process the received query
    return {"message": response},200

@app.route('/convert', methods=['POST'])
def convert_to_pdf():
    data = request.get_json()
    markdown_content = data.get('content', '')
    print(f"Received markdown content: {markdown_content}")
    markdown_content = str(markdown_content)
    convert_to_html(markdown_content)
    if not os.path.exists("Response.html"):
        return {"error": "Failed to generate PDF"}, 500

    return {"message": "PDF generated successfully"}

@app.route('/download-pdf', methods=['GET'])
def download_pdf():
    output_file = 'Response.html'

    # Check if the PDF exists
    if not os.path.exists(output_file):
        return {"error": "PDF not found"}, 40400

    return send_file(output_file, as_attachment=True, download_name='Response.html', mimetype='text/html')

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