from flask import Flask, render_template, request, send_file, jsonify
import json
import os
from io import BytesIO

app = Flask(__name__)

# Load offices from JSON file
def load_offices():
    try:
        with open("officers.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("offices", [])
    except Exception as e:
        return ["कोई कार्यालय उपलब्ध नहीं"]

@app.route('/')
def index():
    offices = load_offices()
    return render_template('index.html', offices=offices)

@app.route('/save_transcript', methods=['POST'])
def save_transcript():
    try:
        data = request.json
        heading = data.get('heading', '').strip()
        transcript = data.get('transcript', '').strip()
        office = data.get('office', '').strip()
        content = f"शीर्षक: {heading}\n\nसंबंधित कार्यालय: {office}\n\nप्रतिलेख:\n{transcript}"
        
        # Create a BytesIO object to serve the file
        buffer = BytesIO()
        buffer.write(content.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name='transcript.txt',
            mimetype='text/plain'
        )
    except Exception as e:
        return jsonify({'error': f'फ़ाइल सहेजने में त्रुटि: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)