"""
Offline Voice-to-Text + Grammar Checker App

A simple desktop application that lets me:
- Record voice using a walkie-talkie style button
- Load audio files and convert them to text
- Manually write or paste text
- Check grammar and get corrected output

All without needing internet access — designed to run fully offline.

I started this little project in order to help me learn how machine learning models work under the hood,
and to build tools that are resilient to poor or unstable internet connections,
like those I experience living in Syria.

By making everything local, I aim to eventually build my own models and services
that I can host and share with others for free or even through Telegram bots.

Built using: Tkinter, Vosk, pyaudio, ffmpeg, language_tool_python
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
import subprocess
import json
import pyaudio
from vosk import Model, KaldiRecognizer
import language_tool_python


class VoiceToTextApp:
    def __init__(self, root):
        #Initialize the app window, load the model and tools.
        
        self.root = root
        self.root.title("Offline Voice-to-Text + Grammar Checker")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        #Speech recognition INPUT setup
        model_path = "vosk-model-small-en-us-0.15"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model '{model_path}' not found. Please download it.")
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)  # The sample rate must match model.

        #Grammar checker setup
        self.tool = language_tool_python.LanguageTool('en-US')  # Supports multiple languages

        #Resetting recording state
        self.is_recording = False
        self.audio_data = b''  # Binary data from microphone

        #Initiate UI elements
        self.create_widgets()



    def create_widgets(self):

        #Upper buttons row
        button_frame = tk.Frame(self.root) 
        button_frame.pack(pady=10) #row

        #record "label"
        #WALKIE TALKIE STYLE FOR EASE of USE
        self.record_label = tk.Label(button_frame, text="Hold to Record", width=15, relief='raised', bg='lightgray')
        self.record_label.pack(side=tk.LEFT, padx=5)
        self.record_label.bind("<ButtonPress-1>", self.start_walkie_talkie_recording)
        self.record_label.bind("<ButtonRelease-1>", self.stop_walkie_talkie_recording)

        #load button
        self.load_btn = tk.Button(button_frame, text="Load Recording", width=15, command=self.load_audio_file)
        self.load_btn.pack(side=tk.LEFT, padx=5)

        #write button
        self.write_btn = tk.Button(button_frame, text="Write Text", width=15, command=self.enable_manual_input)
        self.write_btn.pack(side=tk.LEFT, padx=5)

        #submit button
        self.submit_btn = tk.Button(button_frame, text="Submit", width=15, command=self.submit_text)
        self.submit_btn.pack(side=tk.LEFT, padx=5)

        #Input TextBox
        self.text_box = tk.Text(self.root, height=10, wrap='word', font=("Arial", 12), state='normal')
        self.text_box.pack(padx=10, pady=5, fill='both', expand=True)

        #Line - Separator 
        sep = tk.Frame(self.root, height=2, bd=1, relief='sunken')
        sep.pack(fill='x', padx=10, pady=5)

        #Output Box
        self.placeholder_box = tk.Text(self.root, height=8, wrap='word', font=("Arial", 12))
        self.placeholder_box.pack(padx=10, pady=5, fill='both', expand=True)

        #Lower buttons
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(pady=10)

        #reset button
        self.reset_btn = tk.Button(bottom_frame, text="Reset", width=10, command=self.reset_app)
        self.reset_btn.pack(side=tk.LEFT, padx=5)

        #exit button
        self.exit_btn = tk.Button(bottom_frame, text="Exit", width=10, command=self.root.quit)
        self.exit_btn.pack(side=tk.LEFT, padx=5)

    def reset_app(self):
        #Clearing both input and output boxes
        self.text_box.delete(1.0, tk.END)
        self.placeholder_box.delete(1.0, tk.END)

    def enable_manual_input(self):
        self.reset_app()
        self.text_box.focus_set()

    def run_in_thread(self, func, callback=None):
        #let's stop the app from freezing whenever I call the model or process something
        def worker():
            result = func()
            if callback:
                self.root.after(0, lambda: callback(result))

        threading.Thread(target=worker, daemon=True).start()

    def load_audio_file(self):
        #Handle multi types of audio files
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[("Audio Files", "*.wav *.mp3 *.ogg *.flac *.m4a *.aac")]
        )
        if not file_path:
            return  # like a cancel

        #Must clear output immediately here..
        self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, "Processing audio file...")

        def task():
            try:
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext != ".wav":
                    # Using ffmpeg to convert unsupported formats to WAV for Vosk
                    process = subprocess.run([
                        "ffmpeg", "-i", file_path,
                        "-ar", "16000", "-ac", "1", "-f", "wav", "pipe:1"
                    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    data = process.stdout
                else:
                    with open(file_path, 'rb') as f:
                        data = f.read()

                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                else:
                    text = ""
                return text
            except Exception as e:
                return f"Error: {e}"

        def on_complete(text):
            if text.startswith("Error:"):
                messagebox.showerror("Error", text)
            else:
                self.text_box.delete(1.0, tk.END)
                self.text_box.insert(tk.END, text)

        self.run_in_thread(task, on_complete)

    def start_walkie_talkie_recording(self, event=None):
        self.is_recording = True
        self.record_label.config(relief='sunken', bg='red')
        self.reset_app()
        self.text_box.insert(tk.END, "Recording... Speak now.")
        threading.Thread(target=self.record_microphone).start()

    def stop_walkie_talkie_recording(self, event=None):
        self.is_recording = False
        self.record_label.config(relief='raised', bg='lightgray')

    def record_microphone(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        frames_per_buffer=4096)

        stream.start_stream()

        self.audio_data = b''

        while self.is_recording:
            data = stream.read(4096)
            self.audio_data += data
            if self.recognizer.AcceptWaveform(data):
                pass  # Ignore partial results

        stream.stop_stream()
        stream.close()
        p.terminate()

        #to get final result after recording stops
        final_result = json.loads(self.recognizer.FinalResult())
        text = final_result.get("text", "")

        #To display the recognized text
        self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, text)

    def submit_text(self):
        raw_text = self.text_box.get(1.0, tk.END).strip()
        if not raw_text:
            messagebox.showwarning("No Content", "The input box is empty.")
            return

        self.placeholder_box.delete(1.0, tk.END)
        self.placeholder_box.insert(tk.END, "Checking grammar...")

        def task():
            matches = self.tool.check(raw_text)
            corrected = self.tool.correct(raw_text) if matches else None
            return matches, corrected, raw_text

        def on_complete(result):
            matches, corrected, _ = result
            self.placeholder_box.delete(1.0, tk.END)
            if not matches:
                self.placeholder_box.insert(tk.END, "CORRECT")
            else:
                self.placeholder_box.insert(tk.END, corrected)

        self.run_in_thread(task, on_complete)


#Main App/Loop
if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceToTextApp(root)
    root.mainloop()