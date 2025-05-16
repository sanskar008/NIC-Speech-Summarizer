import tkinter as tk
import speech_recognition as sr
import threading
import os

# Global variable to control recording
recording = False
recognizer = sr.Recognizer()
audio_data = []  # To store audio chunks while recording


# Function to handle the start and stop of speech recognition
def recognize_speech():
    global recording, audio_data
    with sr.Microphone() as source:
        try:
            status_label.config(text="🎙️ Listening...")
            while recording:
                # Capture audio as long as recording is True
                audio = recognizer.listen(
                    source, timeout=5, phrase_time_limit=30
                )  # Customize time limit as needed
                audio_data.append(audio)  # Store the audio chunk
            status_label.config(text="🔄 Transcribing...")

            # After stopping, transcribe the full collected audio data
            full_audio = sr.AudioData(
                b"".join([chunk.get_raw_data() for chunk in audio_data]),
                audio_data[0].sample_rate,
                audio_data[0].sample_width,
            )
            transcript = recognizer.recognize_google(
                full_audio, language="hi-IN"
            )  # Recognizing Hindi speech

            result_text.delete("1.0", tk.END)  # Clear previous transcript
            result_text.insert(tk.END, transcript)  # Insert full transcript

            # Save the transcript to a .txt file
            save_transcript_to_file(transcript)

            status_label.config(text="✅ Done")

        except Exception as e:
            status_label.config(text=f"❌ Error: {e}")


# Function to save the transcript to a .txt file
def save_transcript_to_file(transcript):
    try:
        # Open the file in write mode (this will overwrite the file if it already exists)
        with open("transcript.txt", "w", encoding="utf-8") as file:
            file.write(transcript)  # Write the transcript to the file
        status_label.config(text="✅ Transcript saved to transcript.txt")
    except Exception as e:
        status_label.config(text=f"❌ Error saving file: {e}")


# Start recording in a separate thread
def start_recording():
    global recording, audio_data
    recording = True
    audio_data = []  # Reset audio data each time we start a new recording
    threading.Thread(target=recognize_speech, daemon=True).start()
    status_label.config(text="🎙️ Recording Started...")


# Stop the recording
def stop_recording():
    global recording
    recording = False
    status_label.config(text="🛑 Recording Stopped")


# GUI
root = tk.Tk()
root.title("हिंदी स्पीच ट्रांसक्रिप्शन")
root.geometry("700x500")

tk.Label(root, text="🎤 हिंदी स्पीच ट्रांसक्रिप्शन", font=("Helvetica", 16, "bold")).pack(
    pady=10
)

# Buttons for starting and stopping the recording
tk.Button(
    root, text="🎙️ Start Recording", font=("Helvetica", 12), command=start_recording
).pack(pady=10)
tk.Button(
    root, text="🛑 Stop Recording", font=("Helvetica", 12), command=stop_recording
).pack(pady=10)

status_label = tk.Label(root, text="", font=("Helvetica", 11))
status_label.pack(pady=5)

tk.Label(root, text="📝 पूरा ट्रांसक्रिप्ट:", font=("Helvetica", 12)).pack()
result_text = tk.Text(root, height=10, wrap=tk.WORD, font=("Helvetica", 12))
result_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

root.mainloop()
