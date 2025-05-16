import sys
import threading
import speech_recognition as sr
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from qt_material import apply_stylesheet

# Global variables for recording
recording = False
recognizer = sr.Recognizer()
audio_data = []


class SignalEmitter(QObject):
    update_transcript = pyqtSignal(str)
    update_status = pyqtSignal(str)


class TranscriptionWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("हिंदी स्पीच ट्रांसक्रिप्शन")
        self.setGeometry(100, 100, 700, 500)

        # Create signal emitter
        self.signals = SignalEmitter()

        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title label
        title_label = QLabel("🎤 हिंदी स्पीच ट्रांसक्रिप्शन")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #202124;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Heading input
        self.heading_input = QLineEdit()
        self.heading_input.setPlaceholderText("Enter heading...")
        self.heading_input.setStyleSheet(
            """
            QLineEdit {
                padding: 10px;
                border: 1px solid #dfe1e5;
                border-radius: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
                box-shadow: 0 1px 6px rgba(32, 33, 36, 0.28);
            }
        """
        )
        main_layout.addWidget(QLabel("📌 Heading:"))
        main_layout.addWidget(self.heading_input)

        # Recording buttons layout
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("🎙️ Start Recording")
        self.stop_button = QPushButton("🛑 Stop Recording")
        for btn in [self.start_button, self.stop_button]:
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #1a73e8;
                    color: white;
                    padding: 10px;
                    border-radius: 8px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #1557b0;
                }
                QPushButton:pressed {
                    background-color: #124a93;
                }
            """
            )
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        main_layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: #5f6368;")
        main_layout.addWidget(self.status_label)

        # Transcript area
        main_layout.addWidget(QLabel("📝 Transcript:"))
        self.transcript_area = QTextEdit()
        self.transcript_area.setStyleSheet(
            """
            QTextEdit {
                padding: 10px;
                border: 1px solid #dfe1e5;
                border-radius: 8px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #1a73e8;
                box-shadow: 0 1px 6px rgba(32, 33, 36, 0.28);
            }
        """
        )
        main_layout.addWidget(self.transcript_area)

        # Save button
        self.save_button = QPushButton("💾 Save Transcript")
        self.save_button.setStyleSheet(
            """
            QPushButton {
                background-color: #34a853;
                color: white;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2d9145;
            }
            QPushButton:pressed {
                background-color: #267a3b;
            }
        """
        )
        main_layout.addWidget(self.save_button)

        # Connect signals to slots *after* widgets are created
        self.signals.update_transcript.connect(self.transcript_area.setPlainText)
        self.signals.update_status.connect(self.status_label.setText)

        # Connect buttons
        self.start_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        self.save_button.clicked.connect(self.save_transcript_to_file)

    def recognize_speech(self):
        global recording, audio_data
        with sr.Microphone() as source:
            try:
                self.signals.update_status.emit("🎙️ Listening...")
                while recording:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=30)
                    audio_data.append(audio)
                self.signals.update_status.emit("🔄 Transcribing...")

                full_audio = sr.AudioData(
                    b"".join([chunk.get_raw_data() for chunk in audio_data]),
                    audio_data[0].sample_rate,
                    audio_data[0].sample_width,
                )
                transcript = recognizer.recognize_google(full_audio, language="hi-IN")
                self.signals.update_transcript.emit(transcript)
                self.signals.update_status.emit("✅ Done")
            except Exception as e:
                self.signals.update_status.emit(f"❌ Error: {e}")

    def start_recording(self):
        global recording, audio_data
        recording = True
        audio_data = []
        threading.Thread(target=self.recognize_speech, daemon=True).start()
        self.status_label.setText("🎙️ Recording Started...")

    def stop_recording(self):
        global recording
        recording = False
        self.status_label.setText("🛑 Recording Stopped")

    def save_transcript_to_file(self):
        try:
            heading = self.heading_input.text().strip()
            transcript = self.transcript_area.toPlainText().strip()
            content = f"Heading: {heading}\n\nTranscript:\n{transcript}"
            with open("transcript.txt", "w", encoding="utf-8") as file:
                file.write(content)
            self.status_label.setText("✅ Transcript saved to transcript.txt")
        except Exception as e:
            self.status_label.setText(f"❌ Error saving file: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme="light_blue.xml")  # Material Design styling
    window = TranscriptionWindow()
    window.show()
    sys.exit(app.exec())
