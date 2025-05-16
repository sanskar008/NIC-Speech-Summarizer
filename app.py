import tkinter as tk
from tkinter import messagebox, scrolledtext
import speech_recognition as sr
from transformers import pipeline

# Initialize Summarizer
summarizer = pipeline("summarization", model="csebuetnlp/mT5_multilingual_XLSum")

# Initialize Speech Recognizer
recognizer = sr.Recognizer()

def record_audio():
    with sr.Microphone() as source:
        status_label.config(text="Recording... Speak now.")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, timeout=15)
        return audio

def transcribe_audio(audio):
    try:
        text = recognizer.recognize_google(audio, language="hi-IN")
        return text
    except sr.UnknownValueError:
        return "Sorry, I could not understand the speech."
    except sr.RequestError:
        return "There was an error with the speech recognition service."

def summarize_text(text):
    summary = summarizer(text, max_length=100, min_length=30, do_sample=False)
    return summary[0]['summary_text']

def process_audio():
    audio = record_audio()
    transcript = transcribe_audio(audio)
    summary = summarize_text(transcript)

    transcript_box.delete(1.0, tk.END)
    transcript_box.insert(tk.END, transcript)
    summary_box.delete(1.0, tk.END)
    summary_box.insert(tk.END, summary)

    status_label.config(text="Processing Complete!")

# GUI Setup
root = tk.Tk()
root.title("Hindi Speech-to-Text Summarizer")
root.geometry("600x500")

status_label = tk.Label(root, text="Ready to Record", font=("Arial", 14), fg="green")
status_label.pack(pady=10)

start_button = tk.Button(root, text="🔴 Record and Summarize", command=process_audio, font=("Arial", 14))
start_button.pack(pady=20)

transcript_label = tk.Label(root, text="📝 Transcript", font=("Arial", 12))
transcript_label.pack(pady=10)

transcript_box = scrolledtext.ScrolledText(root, height=8, wrap=tk.WORD, font=("Arial", 12))
transcript_box.pack(fill=tk.BOTH, padx=20, pady=10)

summary_label = tk.Label(root, text="📚 Summary", font=("Arial", 12))
summary_label.pack(pady=10)

summary_box = scrolledtext.ScrolledText(root, height=5, wrap=tk.WORD, font=("Arial", 12))
summary_box.pack(fill=tk.BOTH, padx=20, pady=10)

root.mainloop()
