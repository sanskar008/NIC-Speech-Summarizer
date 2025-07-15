from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
import logging
from supabase import create_client, Client
from datetime import datetime
from flask_socketio import SocketIO, emit
import eventlet
import queue
import threading
from google.cloud import speech

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key")

from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), "nic-rajgarh-025d599c7ab3.json")

# Load officers from JSON
def load_offices():
    try:
        if not os.path.exists("officers.json"):
            print("officers.json not found")
            return []
        with open("officers.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            officers = [
                str(o).replace('"', '\\"').replace("\n", "")
                for o in data.get("offices", [])
            ]
            return officers
    except Exception as e:
        print(f"Error loading officers: {e}")
        return []


# Get user role
def get_user_role():
    user = session.get("user")
    if not user:
        print("No user in session")
        return None
    try:
        role_response = (
            supabase.table("user_roles")
            .select("role")
            .eq("user_id", user["id"])
            .execute()
        )
        print("Role response:", role_response.data)
        return role_response.data[0]["role"] if role_response.data else None
    except Exception as e:
        print(f"Error fetching role: {e}")
        return None


# Get user designations
def get_user_designations(user_id):
    try:
        designations_response = (
            supabase.table("user_designations")
            .select("designation")
            .eq("user_id", user_id)
            .execute()
        )
        designations = (
            [d["designation"] for d in designations_response.data]
            if designations_response.data
            else []
        )
        #print(f"Designations for user {user_id}:", designations)
        return designations
    except Exception as e:
        print(f"Error fetching designations: {e}")
        return []


@app.route("/")
def index():
    user = session.get("user")
    role = get_user_role()
    officers = load_offices()
    return render_template("index.html", user=user, role=role, officers=officers)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            user_data = {
                "id": response.user.id,
                "email": response.user.email,
                "created_at": response.user.created_at,
            }
            #print("Session user:", user_data)
            session["user"] = user_data
            return redirect(url_for("index"))
        except Exception as e:
            return render_template("login.html", error=f"लॉगिन त्रुटि: {str(e)}")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role", "officer")
        designation = request.form.get("designation", "")
        user_pin = request.form.get("user_pin", "")
        master_pin = request.form.get("master_pin", "")
        # Pin validation
        if role == "admin":
            if not master_pin or master_pin != "admin@nic":
                return render_template(
                    "signup.html", error="अमान्य पिन", officers=load_offices()
                )
        else:
            if not user_pin or user_pin != "user@nic":
                return render_template(
                    "signup.html", error="अमान्य पिन", officers=load_offices()
                )
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            user_id = response.user.id
            supabase.table("user_roles").insert(
                {"user_id": user_id, "role": role}
            ).execute()
            if designation:
                supabase.table("user_designations").insert(
                    {"user_id": user_id, "designation": designation}
                ).execute()
            # Save user_pin or master_pin as needed
            if role == "admin":
                print(f"Admin signup with master pin: {master_pin}")
            else:
                print(f"User PIN for {email}: {user_pin}")
            login_response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            user_data = {
                "id": login_response.user.id,
                "email": login_response.user.email,
                "created_at": datetime.now().isoformat(),
            }
            print("Logged in user after signup:", user_data)
            session["user"] = user_data
            return redirect(url_for("index"))
        except Exception as e:
            return render_template(
                "signup.html", error=f"साइनअप त्रुटि: {str(e)}", officers=load_offices()
            )
    return render_template("signup.html", officers=load_offices())


@app.route("/logout")
def logout():
    supabase.auth.sign_out()
    session.pop("user", None)
    return redirect(url_for("index"))


@app.route("/transcripts")
def transcripts():
    user = session.get("user")
    role = get_user_role()
    if not user or role != "admin":
        return redirect(url_for("login"))
    officers = load_offices()
    logging.debug(f"Rendering transcripts with officers: {officers}")
    return render_template("transcripts.html", user=user, role=role, officers=officers)


@app.route("/my_tasks")
def my_tasks():
    if not session.get("user"):
        print("Session user not logged in")
        return redirect(url_for("login"))
    user = session.get("user")
    officers = load_offices()
    return render_template("my_tasks.html", officers=officers, user=user)


@app.route("/save_transcript", methods=["POST"])
def save_transcript():
    if not session.get("user") or get_user_role() != "admin":
        return jsonify({"error": "केवल व्यवस्थापक टास्क बना सकते हैं"}), 403
    try:
        data = request.json
        heading = data.get("heading", "").strip()
        transcript = data.get("transcript", "").strip()
        officers = data.get("officers", [])
        assign_to_all = data.get("assign_to_all", False)
        deadline = data.get("deadline", "").strip()

        if not heading or not transcript or not (officers or assign_to_all):
            return jsonify({"error": "बैठक शीर्षक, प्रतिलेख, और अधिकारी अनिवार्य हैं"}), 400

        deadline_dt = (
            datetime.fromisoformat(deadline.replace("T", " ")) if deadline else None
        )

        task_response = (
            supabase.table("tasks")
            .insert(
                {
                    "heading": heading,
                    "transcript": transcript,
                    "deadline": deadline_dt.isoformat() if deadline_dt else None,
                    "status": "pending",
                }
            )
            .execute()
        )

        if not task_response.data:
            print("No task data returned")
            return jsonify({"error": "टास्क सहेजने में त्रुटि"}), 500

        task_id = task_response.data[0]["id"]

        officers_to_assign = load_offices() if assign_to_all else officers
        if not officers_to_assign:
            return jsonify({"error": "कोई अधिकारी उपलब्ध नहीं"}), 400

        assignments = [
            {"task_id": task_id, "officer": officer} for officer in officers_to_assign
        ]
        assignment_response = (
            supabase.table("task_assignments").insert(assignments).execute()
        )

        if assignment_response.data:
            return jsonify({"message": "टास्क सफलतापूर्वक सहेजा और असाइन किया गया"}), 201
        else:
            print("Error in assignments:", assignments)
            return jsonify({"error": "असाइनमेंट सहेजने में त्रुटि"}), 500
    except Exception as e:
        print(f"Error saving task: {str(e)}")
        return jsonify({"error": f"टास्क सहेजने में त्रुटि: {str(e)}"}), 500


@app.route("/get_transcripts", methods=["GET"])
def get_transcripts():
    if not session.get("user") or get_user_role() != "admin":
        print("Access denied: User not admin", session.get("user"))
        return jsonify({"error": "केवल व्यवस्थापक टास्क देख सकते हैं"}), 403
    try:
        tasks_response = (
            supabase.table("tasks").select("*").order("created_at", desc=True).execute()
        )

        if not tasks_response.data:
            return jsonify([]), 200
        tasks = tasks_response.data
        for task in tasks:
            assignments_response = (
                supabase.table("task_assignments")
                .select("officer, update_comment")
                .eq("task_id", task["id"])
                .execute()
            )
            #print(f"Assignments for task {task['id']}:", assignments_response.data)
            task["assignments"] = (
                assignments_response.data if assignments_response.data else []
            )
        return jsonify(tasks), 200
    except Exception as e:
        print(f"Error fetching transcripts: {str(e)}")
        return jsonify({"error": f"टास्क प्राप्त करने में त्रुटि: {str(e)}"}), 500


@app.route("/get_my_tasks", methods=["GET"])
def get_my_tasks():
    if not session.get("user"):
        return jsonify({"error": "लॉगिन आवश्यक है"}), 401
    try:
        user_id = session["user"]["id"]
        designations = get_user_designations(user_id)
        if not designations:
            print(f"No designations found for user {user_id}")
            return jsonify([]), 200
        tasks_response = (
            supabase.table("tasks").select("*").order("created_at", desc=True).execute()
        )
        if not tasks_response.data:
            print("No tasks found")
            return jsonify([]), 200
        tasks = tasks_response.data
        filtered_tasks = []
        for task in tasks:
            assignments_response = (
                supabase.table("task_assignments")
                .select("officer, update_comment")
                .eq("task_id", task["id"])
                .in_("officer", designations)
                .execute()
            )
            if assignments_response.data:
                task["assignments"] = assignments_response.data
                filtered_tasks.append(task)
        #print("Filtered tasks:", filtered_tasks)
        return jsonify(filtered_tasks), 200
    except Exception as e:
        print(f"Error fetching my tasks: {str(e)}")
        return jsonify({"error": f"टास्क प्राप्त करने में त्रुटि: {str(e)}"}), 500


@app.route("/update_task/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    if not session.get("user"):
        return jsonify({"error": "लॉगिन आवश्यक है"}), 401
    try:
        user_id = session["user"]["id"]
        designations = get_user_designations(user_id)
        data = request.json
        status = data.get("status", "pending")
        update_comment = data.get("update_comment", "").strip()
        officer = data.get("officer", "")

        # Check if task is assigned to the officer
        assignment_response = (
            supabase.table("task_assignments")
            .select("officer")
            .eq("task_id", task_id)
            .eq("officer", officer)
            .execute()
        )
        if not assignment_response.data:
            print(f"Task {task_id} not assigned to officer: {officer}")
            return jsonify({"error": "आपको यह टास्क असाइन नहीं है"}), 403

        # Verify officer is in user's designations
        if officer not in designations:
            print(f"Officer {officer} not in user designations: {designations}")
            return jsonify({"error": "आपके पास यह पदनाम नहीं है"}), 403

        # Update task status
        if status in ["pending", "in_progress", "completed"]:
            supabase.table("tasks").update({"status": status}).eq(
                "id", task_id
            ).execute()
            #print(f"Updated status for task {task_id} to {status}")

        # Update comment
        if update_comment:
            supabase.table("task_assignments").update(
                {"update_comment": update_comment}
            ).eq("task_id", task_id).eq("officer", officer).execute()
            #print(
            #    f"Updated comment for task {task_id}, officer {officer}: {update_comment}"
            #)

        return jsonify({"message": "टास्क सफलतापूर्वक अपडेट किया गया"}), 200
    except Exception as e:
        print(f"Error updating task: {str(e)}")
        return jsonify({"error": f"टास्क अपडेट करने में त्रुटि: {str(e)}"}), 500


@app.route("/update_transcript/<int:id>", methods=["PUT"])
def update_transcript(id):
    if not session.get("user") or get_user_role() != "admin":
        return jsonify({"error": "केवल व्यवस्थापक टास्क अपडेट कर सकते हैं"}), 403
    try:
        data = request.json
        heading = data.get("heading", "").strip()
        transcript = data.get("transcript", "").strip()
        officers = data.get("officers", [])
        assign_to_all = data.get("assign_to_all", False)
        deadline = data.get("deadline", "").strip()

        if not heading or not transcript:
            return jsonify({"error": "बैठक शीर्षक और प्रतिलेख अनिवार्य हैं"}), 400

        deadline_dt = (
            datetime.fromisoformat(deadline.replace("T", " ")) if deadline else None
        )

        task_response = (
            supabase.table("tasks")
            .update(
                {
                    "heading": heading,
                    "transcript": transcript,
                    "deadline": deadline_dt.isoformat() if deadline_dt else None,
                }
            )
            .eq("id", id)
            .execute()
        )

        if not task_response.data:
            print("No task data updated")
            return jsonify({"error": "टास्क अपडेट करने में त्रुटि"}), 500

        supabase.table("task_assignments").delete().eq("task_id", id).execute()

        officers_to_assign = load_offices() if assign_to_all else officers
        if not officers_to_assign:
            return jsonify({"error": "कोई अधिकारी उपलब्ध नहीं"}), 400

        assignments = [
            {"task_id": id, "officer": officer} for officer in officers_to_assign
        ]
        assignment_response = (
            supabase.table("task_assignments").insert(assignments).execute()
        )

        if assignment_response.data:
            return jsonify({"message": "टास्क सफलतापूर्वक अपडेट किया गया"}), 200
        else:
            print("Error in updating assignments:", assignments)
            return jsonify({"error": "असाइनमेंट अपडेट करने में त्रुटि"}), 500
    except Exception as e:
        print(f"Error updating transcript: {str(e)}")
        return jsonify({"error": f"टास्क अपडेट करने में त्रुटि: {str(e)}"}), 500


# New Delete Endpoint
@app.route("/delete_transcript/<id>", methods=["DELETE"])
def delete_transcript(id):
    if not session.get("user") or get_user_role() != "admin":
        return jsonify({"error": "केवल व्यवस्थापक टास्क हटा सकते हैं"}), 403
    try:
        # Delete assignments first to maintain referential integrity
        supabase.table("task_assignments").delete().eq("task_id", id).execute()
        # Delete task
        task_response = supabase.table("tasks").delete().eq("id", id).execute()
        if not task_response.data:
            return jsonify({"error": "टास्क हटाने में त्रुटि"}), 500
        return jsonify({"message": "टास्क सफलतापूर्वक हटाया गया"}), 200
    except Exception as e:
        logging.error(f"Error deleting transcript: {e}")
        return jsonify({"error": f"टास्क हटाने में त्रुटि: {str(e)}"}), 500


@app.route("/debug_officers")
def debug_officers():
    officers = load_offices()
    return jsonify({"officers": officers})


# === Live Speech-to-Text Streaming Handlers ===

@socketio.on('start_stream')
def start_stream():
    if not hasattr(threading.current_thread(), "audio_queue"):
        threading.current_thread().audio_queue = queue.Queue()
    emit('stream_started')

@socketio.on('audio_chunk')
def receive_audio_chunk(data):
    if hasattr(threading.current_thread(), "audio_queue"):
        threading.current_thread().audio_queue.put(data)

@socketio.on('stop_stream')
def stop_stream():
    if hasattr(threading.current_thread(), "audio_queue"):
        threading.current_thread().audio_queue.put(None)

@socketio.on('stream_audio')
def stream_audio():
    audio_queue = queue.Queue()
    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="hi-IN",
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
        single_utterance=False,
    )
    def audio_generator():
        while True:
            chunk = audio_queue.get()
            if chunk is None:
                break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)
    requests = audio_generator()
    responses = client.streaming_recognize(streaming_config, requests)
    for response in responses:
        for result in response.results:
            transcript = result.alternatives[0].transcript
            emit('transcript', {'text': transcript})


if __name__ == "__main__":
    socketio.run(app, debug=True)
