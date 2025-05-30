from flask import Flask, render_template, request, jsonify
import json
import os
from supabase import create_client, Client

app = Flask(__name__)

# Initialize Supabase client
SUPABASE_URL = "https://acououpxdlwiyajydseo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFjb3VvdXB4ZGx3aXlhanlkc2VvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDg2MDU4MjYsImV4cCI6MjA2NDE4MTgyNn0.2RkzONLM_s8fjc24TvT2E3V9DLxf4Xjhw-TAKXRHQ2Q"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# Load offices from JSON file
def load_offices():
    try:
        if not os.path.exists("officers.json"):
            return []
        with open("officers.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("offices", [])
    except Exception as e:
        return []


@app.route("/")
def index():
    offices = load_offices()
    return render_template("index.html", offices=offices)


@app.route("/transcripts")
def transcripts():
    offices = load_offices()
    return render_template("transcripts.html", offices=offices)


@app.route("/save_transcript", methods=["POST"])
def save_transcript():
    try:
        data = request.json
        heading = data.get("heading", "").strip()
        transcript = data.get("transcript", "").strip()
        office = data.get("office", "").strip()

        if not heading or not transcript or not office:
            return jsonify({"error": "शीर्षक, प्रतिलेख, और कार्यालय अनिवार्य हैं"}), 400

        # Insert data into Supabase
        response = (
            supabase.table("transcripts")
            .insert({"heading": heading, "transcript": transcript, "office": office})
            .execute()
        )

        if response.data:
            return jsonify({"message": "प्रतिलेख सफलतापूर्वक डेटाबेस में सहेजा गया"}), 201
        else:
            return jsonify({"error": "डेटाबेस में सहेजने में त्रुटि"}), 500
    except Exception as e:
        return jsonify({"error": f"फ़ाइल सहेजने में त्रुटि: {str(e)}"}), 500


@app.route("/get_transcripts", methods=["GET"])
def get_transcripts():
    try:
        response = (
            supabase.table("transcripts")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        if response.data:
            return jsonify(response.data), 200
        else:
            return jsonify({"error": "कोई प्रतिलेख उपलब्ध नहीं"}), 404
    except Exception as e:
        return jsonify({"error": f"प्रतिलेख प्राप्त करने में त्रुटि: {str(e)}"}), 500


@app.route("/update_transcript/<int:id>", methods=["PUT"])
def update_transcript(id):
    try:
        data = request.json
        heading = data.get("heading", "").strip()
        transcript = data.get("transcript", "").strip()
        office = data.get("office", "").strip()

        if not heading or not transcript or not office:
            return jsonify({"error": "शीर्षक, प्रतिलेख, और कार्यालय अनावर्य हैं"}), 400

        # Update data in Supabase
        response = (
            supabase.table("transcripts")
            .update({"heading": heading, "transcript": transcript, "office": office})
            .eq("id", id)
            .execute()
        )

        if response.data:
            return jsonify({"message": "प्रतिलेख सफलतापूर्वक अपडेट किया गया"}), 200
        else:
            return jsonify({"error": "प्रतिलेख अपडेट करने में त्रुटि"}), 500
    except Exception as e:
        return jsonify({"error": f"प्रतिलेख अपडेट करने में त्रुटि: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
