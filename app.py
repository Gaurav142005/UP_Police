from flask import Flask, request, send_file
from flask_cors import CORS
from convert import convert_to_html
import os
import json
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

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080, debug=True)  # Run Flask server on port 5001