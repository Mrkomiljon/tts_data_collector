import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import sounddevice as sd
import soundfile as sf
import os
import threading
import time

samplerate = 48000   
channels = 1
recording = False
audio_data = []
texts = []
current_index = 0
completed_indices = set()

os.makedirs("audio", exist_ok=True)
os.makedirs("text", exist_ok=True)

def find_completed_indices():
    completed = set()
    for filename in os.listdir("audio"):
        if filename.endswith(".wav") and filename.startswith("utt_"):
            try:
                index = int(filename[4:8])
                completed.add(index)
            except:
                continue
    return completed

def check_microphone():
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if not input_devices:
            messagebox.showerror("Mikrofon topilmadi", "❌ Mikrofon qurilmasi aniqlanmadi. Iltimos, mikrofonni ulang yoki faollashtiring.")
            return False
        return True
    except Exception as e:
        messagebox.showerror("Xatolik", f"Mikrofonni tekshirishda xatolik:\n{str(e)}")
        return False

def load_texts():
    global texts, current_index, completed_indices
    try:
        file_path = filedialog.askopenfilename(
            title="Matn faylini tanlang", 
            filetypes=[("Excel yoki CSV", "*.csv *.xlsx")]
        )
        if not file_path:
            return

        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path)
        else:
            messagebox.showerror("Xatolik", "Faqat CSV yoki Excel fayllar qo‘llab-quvvatlanadi.")
            return

        if 'text' not in df.columns:
            first_col = df.columns[0]
            messagebox.showwarning("Ogohlantirish", f"'text' ustuni topilmadi. '{first_col}' ustuni matn sifatida qabul qilinadi.")
            df.rename(columns={first_col: 'text'}, inplace=True)

        raw_texts = df['text'].dropna().tolist()
        if not raw_texts:
            messagebox.showerror("Xatolik", "Matnlar topilmadi.")
            return

        # 🔐 Fayl nomini logda saqlash
        log_file = "log_last_used_file.txt"
        is_new_file = True
        file_name_only = os.path.basename(file_path)

        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                last_file = f.read().strip()
            if last_file == file_name_only:
                is_new_file = False

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(file_name_only)

        if is_new_file:
            completed_indices = set()
            current_index = 0
        else:
            completed_indices = find_completed_indices()
            current_index = len(completed_indices)

        texts.clear()
        texts.extend([text for i, text in enumerate(raw_texts) if i not in completed_indices])

        if texts:
            label.config(text=texts[0])
            status_label.config(text="📌 Matn yuklandi.")
            start_button.config(state=tk.NORMAL)
            stop_button.config(state=tk.DISABLED)
        else:
            label.config(text="🎉 Barcha matnlar yozib olingan.")
            start_button.config(state=tk.DISABLED)
            stop_button.config(state=tk.DISABLED)

    except Exception as e:
        messagebox.showerror("Xatolik", f"Faylni yuklashda xatolik:\n{str(e)}")

def record_audio():
    global audio_data, recording
    audio_data = []
    recording = True

    def callback(indata, frames, time, status):
        if recording:
            audio_data.append(indata.copy())

    try:
        with sd.InputStream(samplerate=samplerate, channels=channels, callback=callback):
            while recording:
                sd.sleep(100)
    except Exception as e:
        messagebox.showerror("Xatolik", f"Audio yozishda muammo:\n{str(e)}")
        recording = False

def start_recording():
    if not check_microphone():
        return
    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    status_label.config(text="🎙️ Yozilmoqda...")
    threading.Thread(target=record_audio).start()

def stop_recording():
    global recording, current_index, audio_data
    if not recording:
        return

    stop_button.config(state=tk.DISABLED)
    recording = False
    time.sleep(0.5)

    if not audio_data:
        status_label.config(text="⚠️ Ovoz yozilmadi")
        messagebox.showerror("Xatolik", "Ovoz yozib olinmadi. Mikrofon ulanganligiga ishonch hosil qiling.")
        start_button.config(state=tk.NORMAL)
        return

    full_index = len(completed_indices)

    audio_filename = f"audio/utt_{full_index:04}.wav"
    text_filename = f"text/utt_{full_index:04}.txt"

    try:
        sf.write(audio_filename, b''.join(audio_data), samplerate)
        with open(text_filename, 'w', encoding='utf-8') as f:
            f.write(texts[current_index])
        status_label.config(text=f"✅ Saqlandi: utt_{full_index:04}")
    except Exception as e:
        messagebox.showerror("Xatolik", f"Faylni saqlashda muammo:\n{str(e)}")
        status_label.config(text="❌ Xatolik!")
        start_button.config(state=tk.NORMAL)
        return

    completed_indices.add(full_index)
    current_index += 1

    if current_index < len(texts):
        label.config(text=texts[current_index])
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        status_label.config(text="📢 Keyingi matn tayyor.")
    else:
        label.config(text="✅ Barcha matnlar yozib olindi.")
        status_label.config(text="🏁 Yozuv tugadi.")
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.DISABLED)

# GUI
root = tk.Tk()
root.title("TTS Dataset Recorder")
root.geometry("600x350")

load_button = tk.Button(root, text="📂 Matn faylini yuklash", font=("Arial", 14), command=load_texts)
load_button.pack(pady=10)

label = tk.Label(root, text="Matn bu yerda chiqadi", font=("Arial", 16), wraplength=500, justify="center")
label.pack(pady=10)

start_button = tk.Button(root, text="🎙️ Start", font=("Arial", 14, "bold"), bg="#4CAF50", fg="white", command=start_recording, state=tk.DISABLED)
start_button.pack(pady=5)

stop_button = tk.Button(root, text="⏹️ Stop", font=("Arial", 14, "bold"), bg="#F44336", fg="white", command=stop_recording, state=tk.DISABLED)
stop_button.pack(pady=5)

status_label = tk.Label(root, text="", font=("Arial", 12), fg="blue")
status_label.pack(pady=10)

root.mainloop()
