from flask import Flask, render_template, request, jsonify
import json
import os
from dotenv import load_dotenv
from supabase import create_client, Client

app = Flask(__name__)

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# Load officers from JSON file
def load_offices():
    try:
        if not os.path.exists("officers.json"):
            return ["कोई कार्यालय उपलब्ध नहीं"]
        with open("officers.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get("offices", ["कोई कार्यालय उपलब्ध नहीं"])
    except Exception as e:
        return ["कोई कार्यालय उपलब्ध नहीं"]


@app.route("/")
def index():
    officers = load_offices()
    return render_template("index.html", officers=officers)


@app.route("/transcripts")
def transcripts():
    officers = load_offices()  # Pass officers to transcripts.html
    return render_template("transcripts.html", officers=officers)


@app.route("/save_transcript", methods=["POST"])
def save_transcript():
    try:
        data = request.json
        heading = data.get("heading", "").strip()
        transcript = data.get("transcript", "").strip()
        officers = data.get("officers", [])  # List of selected officers
        assign_to_all = data.get("assign_to_all", False)

        if not heading or not transcript:
            return jsonify({"error": "शीर्षक और प्रतिलेख अनिवार्य हैं"}), 400

        # Insert task into tasks table
        task_response = (
            supabase.table("tasks")
            .insert({"heading": heading, "transcript": transcript})
            .execute()
        )

        if not task_response.data:
            return jsonify({"error": "टास्क सहेजने में त्रुटि"}), 500

        task_id = task_response.data[0]["id"]

        # Assign to officers
        officers_to_assign = load_offices() if assign_to_all else officers
        if not officers_to_assign:
            return jsonify({"error": "कोई अधिकारी उपलब्ध नहीं"}), 400

        # Insert assignments into task_assignments table
        assignments = [
            {"task_id": task_id, "officer": officer} for officer in officers_to_assign
        ]
        assignment_response = (
            supabase.table("task_assignments").insert(assignments).execute()
        )

        if assignment_response.data:
            return jsonify({"message": "टास्क सफलतापूर्वक सहेजा और असाइन किया गया"}), 201
        else:
            return jsonify({"error": "असाइनमेंट सहेजने में त्रुटि"}), 500
    except Exception as e:
        return jsonify({"error": f"टास्क सहेजने में त्रुटि: {str(e)}"}), 500


@app.route("/get_transcripts", methods=["GET"])
def get_transcripts():
    try:
        # Fetch tasks
        tasks_response = (
            supabase.table("tasks").select("*").order("created_at", desc=True).execute()
        )
        if not tasks_response.data:
            return jsonify([]), 200

        tasks = tasks_response.data

        # Fetch assignments for each task
        for task in tasks:
            assignments_response = (
                supabase.table("task_assignments")
                .select("officer")
                .eq("task_id", task["id"])
                .execute()
            )
            task["officers"] = (
                [assignment["officer"] for assignment in assignments_response.data]
                if assignments_response.data
                else []
            )

        return jsonify(tasks), 200
    except Exception as e:
        return jsonify({"error": f"टास्क प्राप्त करने में त्रुटि: {str(e)}"}), 500


@app.route("/update_transcript/<int:id>", methods=["PUT"])
def update_transcript(id):
    try:
        data = request.json
        heading = data.get("heading", "").strip()
        transcript = data.get("transcript", "").strip()
        officers = data.get("officers", [])
        assign_to_all = data.get("assign_to_all", False)

        if not heading or not transcript:
            return jsonify({"error": "शीर्षक और प्रतिलेख अनिवार्य हैं"}), 400

        # Update task in tasks table
        task_response = (
            supabase.table("tasks")
            .update({"heading": heading, "transcript": transcript})
            .eq("id", id)
            .execute()
        )

        if not task_response.data:
            return jsonify({"error": "टास्क अपडेट करने में त्रुटि"}), 500

        # Delete existing assignments
        supabase.table("task_assignments").delete().eq("task_id", id).execute()

        # Assign to officers
        officers_to_assign = load_offices() if assign_to_all else officers
        if not officers_to_assign:
            return jsonify({"error": "कोई अधिकारी उपलब्ध नहीं"}), 400

        # Insert new assignments
        assignments = [
            {"task_id": id, "officer": officer} for officer in officers_to_assign
        ]
        assignment_response = (
            supabase.table("task_assignments").insert(assignments).execute()
        )

        if assignment_response.data:
            return jsonify({"message": "टास्क सफलतापूर्वक अपडेट किया गया"}), 200
        else:
            return jsonify({"error": "असाइनमेंट अपडेट करने में त्रुटि"}), 500
    except Exception as e:
        return jsonify({"error": f"टास्क अपडेट करने में त्रुटि: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
