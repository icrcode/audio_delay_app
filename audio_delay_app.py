import tkinter as tk
from tkinter import ttk, messagebox
import pyaudio
import numpy as np
import json
import os
from collections import deque
import time
import sys

class AudioDelayApp:
    def __init__(self, master):
        self.master = master
        master.title("Rádio Delay Pro")
        master.geometry("600x450")
        master.resizable(False, False)

        # Configurar ícone do aplicativo
        try:
            if getattr(sys, '_MEIPASS', False):
                # Executando a partir de um executável compilado pelo PyInstaller
                icon_path = os.path.join(sys._MEIPASS, "mic.ico")
            else:
                # Executando como script
                icon_path = os.path.join(os.path.dirname(__file__), "mic.ico")
            master.iconbitmap(icon_path)
        except Exception as e:
            print(f"Erro ao carregar ícone: {e}")

        self.p = None
        self.stream = None
        self.running = False
        self.bypass_active = True
        self.buffer = deque(maxlen=44100 * 60)  # Limite máximo de 60 segundos de buffer

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100

        self.input_devices = []
        self.output_devices = []
        self.load_audio_devices()

        # Estilo com nova paleta de cores
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1E2A44")  # Azul escuro
        style.configure("TLabel", background="#1E2A44", foreground="#FFFFFF", font=("Arial", 11))
        style.configure("TButton", font=("Arial", 11, "bold"), padding=8, background="#007BFF", foreground="#FFFFFF")  # Azul claro
        style.map("TButton", background=[("active", "#0056b3")])
        style.configure("TEntry", font=("Arial", 11), fieldbackground="#2A4066", foreground="#FFFFFF")
        style.configure("TCombobox", font=("Arial", 11), fieldbackground="#2A4066", foreground="#FFFFFF")
        style.configure("Error.TLabel", background="#1E2A44", foreground="#FF5555", font=("Arial", 10))

        # Frame principal
        main_frame = ttk.Frame(master, padding="15", style="TFrame")
        main_frame.pack(fill="both", expand=True)

        # Título
        title_frame = ttk.Frame(main_frame, style="TFrame")
        title_frame.pack(pady=10)
        ttk.Label(title_frame, text="Rádio Delay Pro", font=("Arial", 20, "bold")).pack()
        ttk.Label(title_frame, text="Versão 1.0.2 - © Eng RBS Rádios by Maiko Costa", font=("Arial", 12)).pack()

        # Status
        self.status_var = tk.StringVar(value="Áudio Parado")
        ttk.Label(main_frame, textvariable=self.status_var, font=("Arial", 10, "italic")).pack(pady=5)

        # Mensagem de erro
        self.error_var = tk.StringVar(value="")
        ttk.Label(main_frame, textvariable=self.error_var, style="Error.TLabel").pack(pady=5)

        # Configurações de Delay
        delay_frame = ttk.LabelFrame(main_frame, text="Configurar Delay", padding="10")
        delay_frame.pack(pady=10, padx=10, fill="x")

        delay_input_subframe = ttk.Frame(delay_frame, style="TFrame")
        delay_input_subframe.pack(pady=5)

        # Validação de entradas
        vcmd = (master.register(self.validate_number), "%P", "%W")

        ttk.Label(delay_input_subframe, text="Minutos:").grid(row=0, column=0, padx=5, pady=2)
        self.minutes_entry = ttk.Entry(delay_input_subframe, width=5, validate="key", validatecommand=vcmd)
        self.minutes_entry.insert(0, "0")
        self.minutes_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(delay_input_subframe, text="Segundos:").grid(row=0, column=2, padx=5, pady=2)
        self.seconds_entry = ttk.Entry(delay_input_subframe, width=5, validate="key", validatecommand=vcmd)
        self.seconds_entry.insert(0, "0")
        self.seconds_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(delay_input_subframe, text="Milissegundos:").grid(row=0, column=4, padx=5, pady=2)
        self.milliseconds_entry = ttk.Entry(delay_input_subframe, width=5, validate="key", validatecommand=vcmd)
        self.milliseconds_entry.insert(0, "0")
        self.milliseconds_entry.grid(row=0, column=5, padx=5, pady=2)

        # Dispositivos de Áudio
        devices_frame = ttk.LabelFrame(main_frame, text="Dispositivos de Áudio", padding="10")
        devices_frame.pack(pady=10, padx=10, fill="x")

        ttk.Label(devices_frame, text="Entrada:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.input_device_var = tk.StringVar(master)
        self.input_device_dropdown = ttk.Combobox(devices_frame, textvariable=self.input_device_var, values=[d["name"] for d in self.input_devices], state="readonly")
        if self.input_devices:
            self.input_device_var.set(self.input_devices[0]["name"])
        self.input_device_dropdown.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(devices_frame, text="Saída:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.output_device_var = tk.StringVar(master)
        self.output_device_dropdown = ttk.Combobox(devices_frame, textvariable=self.output_device_var, values=[d["name"] for d in self.output_devices], state="readonly")
        if self.output_devices:
            self.output_device_var.set(self.output_devices[0]["name"])
        self.output_device_dropdown.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        devices_frame.grid_columnconfigure(1, weight=1)

        # Botões de Controle
        control_buttons_frame = ttk.Frame(main_frame, style="TFrame")
        control_buttons_frame.pack(pady=10)

        self.bypass_button = ttk.Button(control_buttons_frame, text="Bypass", command=self.toggle_bypass, style="TButton")
        self.bypass_button.pack(side="left", padx=10)

        self.start_button = ttk.Button(control_buttons_frame, text="Iniciar Delay", command=self.start_audio, style="TButton")
        self.start_button.pack(side="left", padx=10)

        self.stop_button = ttk.Button(control_buttons_frame, text="Parar Áudio", command=self.stop_audio, style="TButton")
        self.stop_button.pack(side="left", padx=10)
        self.stop_button.config(state=tk.DISABLED)

        # VU Meters
        vu_meters_frame = ttk.Frame(main_frame, style="TFrame")
        vu_meters_frame.pack(pady=10)

        ttk.Label(vu_meters_frame, text="Entrada de Áudio:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.input_vu = tk.Canvas(vu_meters_frame, width=30, height=100, bg="#2A4066", highlightthickness=0)
        self.input_vu.pack(side="left", padx=5)
        self.draw_vu_scale(self.input_vu)

        ttk.Label(vu_meters_frame, text="Saída de Áudio:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.output_vu = tk.Canvas(vu_meters_frame, width=30, height=100, bg="#2A4066", highlightthickness=0)
        self.output_vu.pack(side="left", padx=5)
        self.draw_vu_scale(self.output_vu)

        # Rodapé
        footer_frame = ttk.Frame(master, style="TFrame")
        footer_frame.pack(side="bottom", fill="x", pady=5)
        ttk.Label(footer_frame, text="Eng RBS Rádios", font=("Arial", 9), anchor="e").pack(fill="x", padx=10)

        # Carregar configurações após criar widgets
        self.load_config()

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configura estado inicial
        self.set_input_states(tk.NORMAL)

    def validate_number(self, value, widget_name):
        if value == "":
            return True
        try:
            num = int(value)
            if "minutes_entry" in widget_name or "seconds_entry" in widget_name:
                return 0 <= num <= 59
            elif "milliseconds_entry" in widget_name:
                return 0 <= num <= 999
            return True
        except ValueError:
            return False

    def load_config(self):
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
                    self.minutes_entry.delete(0, tk.END)
                    self.minutes_entry.insert(0, config.get("minutes", "0"))
                    self.seconds_entry.delete(0, tk.END)
                    self.seconds_entry.insert(0, config.get("seconds", "0"))
                    self.milliseconds_entry.delete(0, tk.END)
                    self.milliseconds_entry.insert(0, config.get("milliseconds", "0"))
                    if config.get("input_device") in [d["name"] for d in self.input_devices]:
                        self.input_device_var.set(config.get("input_device"))
                    if config.get("output_device") in [d["name"] for d in self.output_devices]:
                        self.output_device_var.set(config.get("output_device"))
        except Exception as e:
            self.error_var.set(f"Erro ao carregar configurações: {e}")

    def save_config(self):
        config = {
            "minutes": self.minutes_entry.get(),
            "seconds": self.seconds_entry.get(),
            "milliseconds": self.milliseconds_entry.get(),
            "input_device": self.input_device_var.get(),
            "output_device": self.output_device_var.get()
        }
        try:
            with open("config.json", "w") as f:
                json.dump(config, f)
        except Exception as e:
            self.error_var.set(f"Erro ao salvar configurações: {e}")

    def load_audio_devices(self):
        try:
            self.p = pyaudio.PyAudio()
            info = self.p.get_host_api_info_by_index(0)
            num_devices = info.get("deviceCount")
            self.input_devices = []
            self.output_devices = []
            for i in range(num_devices):
                device_info = self.p.get_device_info_by_host_api_device_index(0, i)
                device_info["index"] = i
                if device_info.get("maxInputChannels") > 0:
                    self.input_devices.append(device_info)
                if device_info.get("maxOutputChannels") > 0:
                    self.output_devices.append(device_info)
        except Exception as e:
            self.error_var.set(f"Erro ao carregar dispositivos: {e}")

    def draw_vu_scale(self, canvas):
        height = canvas.winfo_height()
        for db in [-40, -30, -20, -10, 0]:
            level = 1 - (db + 40) / 40
            y = height * level
            canvas.create_line(0, y, 10, y, fill="#FFFFFF")
            canvas.create_text(15, y, text=f"{db} dB", fill="#FFFFFF", font=("Arial", 8), anchor="w")

    def audio_callback(self, in_data, frame_count, time_info, status):
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        peak = np.amax(np.abs(audio_data)) / 32768.0
        level = 20 * np.log10(peak) if peak > 0 else -40
        level = max(0, (level + 40) / 40)
        self.update_vu_meter(self.input_vu, level)

        out_data = in_data
        if not self.bypass_active:
            self.buffer.append(in_data)
            try:
                minutes = int(self.minutes_entry.get() or 0)
                seconds = int(self.seconds_entry.get() or 0)
                milliseconds = int(self.milliseconds_entry.get() or 0)
                total_delay_ms = (minutes * 60 * 1000) + (seconds * 1000) + milliseconds
                delay_frames = int(total_delay_ms / 1000 * self.RATE)
                if len(self.buffer) * self.CHUNK > delay_frames:
                    out_data = self.buffer.popleft()
                else:
                    out_data = np.zeros(frame_count * self.CHANNELS, dtype=np.int16).tobytes()
            except ValueError:
                out_data = in_data

        output_audio_data = np.frombuffer(out_data, dtype=np.int16)
        output_peak = np.amax(np.abs(output_audio_data)) / 32768.0
        output_level = 20 * np.log10(output_peak) if output_peak > 0 else -40
        output_level = max(0, (output_level + 40) / 40)
        self.update_vu_meter(self.output_vu, output_level)

        return (out_data, pyaudio.paContinue)

    def update_vu_meter(self, canvas, level):
        canvas.delete("vu")
        height = canvas.winfo_height()
        width = canvas.winfo_width()
        fill_height = int(height * level)
        canvas.create_rectangle(0, height - fill_height, width, height, fill="#00FF00", outline="", tags="vu")
        if level > 0.6:
            canvas.create_rectangle(0, height - int(height * 0.8), width, height - int(height * 0.6), fill="#FFFF00", outline="", tags="vu")
        if level > 0.8:
            canvas.create_rectangle(0, height - int(height * 1.0), width, height - int(height * 0.8), fill="#FF0000", outline="", tags="vu")

    def toggle_bypass(self):
        if not self.running:
            self.start_stream(bypass=True)
        else:
            self.bypass_active = True
            self.status_var.set("Bypass Ativo")
            self.bypass_button.config(text="Bypass")
            self.start_button.config(text="Iniciar Delay")
            self.set_input_states(tk.NORMAL)
            self.save_config()

    def start_audio(self):
        if not self.running:
            self.start_stream(bypass=False)
        else:
            self.bypass_active = False
            self.status_var.set(f"Delay Ativo ({self.minutes_entry.get()}m {self.seconds_entry.get()}s {self.milliseconds_entry.get()}ms)")
            self.bypass_button.config(text="Bypass")
            self.start_button.config(text="Iniciar Delay")
            self.set_input_states(tk.DISABLED)
            self.save_config()

    def start_stream(self, bypass):
        try:
            input_device_index = None
            output_device_index = None
            for d in self.input_devices:
                if d["name"] == self.input_device_var.get():
                    input_device_index = d["index"]
                    break
            for d in self.output_devices:
                if d["name"] == self.output_device_var.get():
                    output_device_index = d["index"]
                    break

            if input_device_index is None or output_device_index is None:
                self.error_var.set("Dispositivo de entrada ou saída não encontrado.")
                return

            if self.p:
                self.p.terminate()
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                output=True,
                input_device_index=input_device_index,
                output_device_index=output_device_index,
                frames_per_buffer=self.CHUNK,
                stream_callback=self.audio_callback
            )
            self.stream.start_stream()
            self.running = True
            self.bypass_active = bypass
            self.status_var.set("Bypass Ativo" if self.bypass_active else f"Delay Ativo ({self.minutes_entry.get()}m {self.seconds_entry.get()}s {self.milliseconds_entry.get()}ms)")
            self.start_button.config(state=tk.NORMAL if not self.bypass_active else tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.bypass_button.config(state=tk.NORMAL)
            self.set_input_states(tk.DISABLED if not self.bypass_active else tk.NORMAL)
            self.save_config()
        except Exception as e:
            self.error_var.set(f"Erro ao iniciar áudio: {e}")

    def stop_audio(self):
        if not self.running:
            return
        self.running = False
        try:
            if self.stream and self.stream.is_active():
                self.stream.stop_stream()
                time.sleep(0.1)  # Pequeno atraso para permitir que o stream pare
            if self.stream:
                self.stream.close()
        except Exception as e:
            self.error_var.set(f"Erro ao parar áudio: {e} - Forçando fechamento.")
            if self.stream:
                self.stream.close()  # Força o fechamento mesmo com erro
        finally:
            if self.p:
                self.p.terminate()
                self.p = None
            self.buffer.clear()
            self.status_var.set("Áudio Parado")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.bypass_button.config(state=tk.DISABLED)
            self.set_input_states(tk.NORMAL)
            self.save_config()

    def set_input_states(self, state):
        self.minutes_entry.config(state=state)
        self.seconds_entry.config(state=state)
        self.milliseconds_entry.config(state=state)
        self.input_device_dropdown.config(state=state)
        self.output_device_dropdown.config(state=state)

    def on_closing(self):
        self.stop_audio()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioDelayApp(root)
    root.mainloop()