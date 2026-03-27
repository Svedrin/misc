import math
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import numpy as np
import sounddevice as sd
from pydub import AudioSegment


class MP3VisualizerApp:
    def __init__(self, root, filename: str):
        self.root = root
        self.root.title("MP3 Visualizer")
        self.root.geometry("1000x500")
        self.root.configure(bg="black")

        self.filename = filename

        # Audio / Playback
        self.audio = None
        self.sample_rate = None
        self.samples = None
        self.channels = 1
        self.total_frames = 0
        self.playhead = 0
        self.stream = None
        self.playing = False
        self.start_time = None

        # Visualizer config
        self.fft_size = 4096
        self.bar_count = 32
        self.update_interval_ms = 30

        # GUI
        self.canvas = tk.Canvas(
            self.root,
            bg="black",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.info_label = tk.Label(
            self.root,
            text="Lade Datei...",
            bg="black",
            fg="white",
            anchor="w"
        )
        self.info_label.pack(fill="x", padx=8, pady=4)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<space>", self.toggle_pause)

        self.load_audio()
        self.start_playback()
        self.update_visualizer()

    def load_audio(self):
        try:
            audio = AudioSegment.from_file(self.filename)
        except Exception as e:
            messagebox.showerror(
                "Fehler beim Laden",
                f"Die MP3-Datei konnte nicht geladen werden:\n\n{e}\n\n"
                "Hinweis: Für pydub wird meist ffmpeg benötigt."
            )
            self.root.destroy()
            return

        # In Mono umwandeln, damit die FFT einfacher wird
        audio = audio.set_channels(1)

        self.audio = audio
        self.sample_rate = audio.frame_rate
        self.channels = audio.channels

        raw = np.array(audio.get_array_of_samples())

        # Normierung je nach Samplebreite
        max_val = float(1 << (8 * audio.sample_width - 1))
        self.samples = raw.astype(np.float32) / max_val

        self.total_frames = len(self.samples)

        duration = self.total_frames / self.sample_rate
        self.info_label.config(
            text=(
                f"Datei: {self.filename} | "
                f"Samplerate: {self.sample_rate} Hz | "
                f"Dauer: {duration:.1f} s | "
                f"Leertaste = Pause/Fortsetzen"
            )
        )

    def audio_callback(self, outdata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)

        if not self.playing:
            outdata[:] = np.zeros((frames, 1), dtype=np.float32)
            return

        end = self.playhead + frames
        chunk = self.samples[self.playhead:end]

        if len(chunk) < frames:
            padded = np.zeros(frames, dtype=np.float32)
            padded[:len(chunk)] = chunk
            outdata[:] = padded.reshape(-1, 1)

            self.playhead = self.total_frames
            self.playing = False

            # Stream nach Ende sauber stoppen
            self.root.after(0, self.stop_stream_after_finish)
        else:
            outdata[:] = chunk.reshape(-1, 1)
            self.playhead = end

    def start_playback(self):
        try:
            self.playing = True
            self.start_time = time.time()

            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=self.audio_callback,
                blocksize=1024
            )
            self.stream.start()
        except Exception as e:
            messagebox.showerror(
                "Fehler bei der Wiedergabe",
                f"Die Audioausgabe konnte nicht gestartet werden:\n\n{e}"
            )
            self.root.destroy()

    def stop_stream_after_finish(self):
        if self.stream is not None:
            try:
                self.stream.stop()
            except Exception:
                pass
        self.info_label.config(text=self.info_label.cget("text") + " | Fertig")

    def toggle_pause(self, event=None):
        self.playing = not self.playing

    def get_current_window(self):
        # Fenster um aktuelle Position für FFT
        center = self.playhead
        half = self.fft_size // 2

        start = max(0, center - half)
        end = min(self.total_frames, start + self.fft_size)

        window = self.samples[start:end]

        if len(window) < self.fft_size:
            padded = np.zeros(self.fft_size, dtype=np.float32)
            padded[:len(window)] = window
            window = padded

        return window

    def compute_bars(self):
        window = self.get_current_window()

        # Fensterfunktion gegen harte Kanten
        window = window * np.hanning(len(window))

        spectrum = np.fft.rfft(window)
        magnitudes = np.abs(spectrum)

        freqs = np.fft.rfftfreq(len(window), d=1.0 / self.sample_rate)

        # Nur sinnvoller Hörbereich
        min_freq = 20
        max_freq = min(16000, self.sample_rate // 2)

        # logarithmisch verteilte Frequenzbänder
        edges = np.logspace(
            math.log10(min_freq),
            math.log10(max_freq),
            self.bar_count + 1
        )

        bars = []
        for i in range(self.bar_count):
            low = edges[i]
            high = edges[i + 1]
            idx = np.where((freqs >= low) & (freqs < high))[0]

            if len(idx) == 0:
                value = 0.0
            else:
                value = np.mean(magnitudes[idx])

            bars.append(value)

        bars = np.array(bars, dtype=np.float32)

        # logarithmische Kompression für bessere Optik
        bars = np.log1p(bars * 20.0)

        # auf 0..1 normieren
        max_bar = np.max(bars)
        if max_bar > 0:
            bars /= max_bar

        return bars

    def draw_bars(self, bars):
        self.canvas.delete("all")

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width < 10 or height < 10:
            return

        gap = 4
        total_gap = gap * (self.bar_count + 1)
        bar_width = max(2, (width - total_gap) / self.bar_count)

        for i, value in enumerate(bars):
            x1 = gap + i * (bar_width + gap)
            x2 = x1 + bar_width

            bar_height = value * (height - 20)
            y1 = height - bar_height
            y2 = height

            # einfache Farb-Abstufung über die Höhe
            if value < 0.33:
                color = "#44ff44"
            elif value < 0.66:
                color = "#ffff44"
            else:
                color = "#ff4444"

            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, width=0)

    def update_visualizer(self):
        if self.total_frames > 0:
            bars = self.compute_bars()
            self.draw_bars(bars)

        self.root.after(self.update_interval_ms, self.update_visualizer)

    def on_close(self):
        try:
            self.playing = False
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
        except Exception:
            pass
        self.root.destroy()


def choose_file():
    return filedialog.askopenfilename(
        title="MP3-Datei auswählen",
        filetypes=[("MP3-Dateien", "*.mp3"), ("Alle Dateien", "*.*")]
    )


def main():
    # Erst verstecktes Root für Dateiauswahl
    pre_root = tk.Tk()
    pre_root.withdraw()

    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = choose_file()

    pre_root.destroy()

    if not filename:
        return

    root = tk.Tk()
    app = MP3VisualizerApp(root, filename)
    root.mainloop()


if __name__ == "__main__":
    main()
