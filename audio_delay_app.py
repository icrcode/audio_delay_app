import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np
import threading
import time
from collections import deque

class AudioDelayApp:
    def __init__(self, master):
        self.master = master
        master.title("Audio Delay App")
        master.geometry("600x450") # Aumentando o tamanho da janela
        master.resizable(False, False) # Desabilitar redimensionamento

        self.p = None # Instância do PyAudio
        self.stream = None
        self.running = False
        self.buffer = deque()

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100

        self.input_devices = []
        self.output_devices = []
        self.load_audio_devices()

        # Estilo para os widgets
        style = ttk.Style()
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        style.configure("TButton", font=("Arial", 10, "bold"))
        style.configure("TEntry", font=("Arial", 10))
        style.configure("TCombobox", font=("Arial", 10))
        style.configure("TLabelFrame", font=("Arial", 12, "bold"))

        # Frame principal
        main_frame = ttk.Frame(master, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Configurações de Delay
        delay_frame = ttk.LabelFrame(main_frame, text="Configurações de Delay", padding="10")
        delay_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ttk.Label(delay_frame, text="Segundos:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.seconds_entry = ttk.Entry(delay_frame, width=10)
        self.seconds_entry.insert(0, "0")
        self.seconds_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(delay_frame, text="Milissegundos:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.milliseconds_entry = ttk.Entry(delay_frame, width=10)
        self.milliseconds_entry.insert(0, "0")
        self.milliseconds_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        delay_frame.grid_columnconfigure(1, weight=1)
        delay_frame.grid_columnconfigure(3, weight=1)

        # Seleção de Dispositivos de Áudio
        devices_frame = ttk.LabelFrame(main_frame, text="Seleção de Dispositivos de Áudio", padding="10")
        devices_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ttk.Label(devices_frame, text="Entrada:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.input_device_var = tk.StringVar(master)
        self.input_device_dropdown = ttk.Combobox(devices_frame, textvariable=self.input_device_var, values=[d["name"] for d in self.input_devices], state="readonly")
        if self.input_devices:
            self.input_device_var.set(self.input_devices[0]["name"])
        self.input_device_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(devices_frame, text="Saída:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.output_device_var = tk.StringVar(master)
        self.output_device_dropdown = ttk.Combobox(devices_frame, textvariable=self.output_device_var, values=[d["name"] for d in self.output_devices], state="readonly")
        if self.output_devices:
            self.output_device_var.set(self.output_devices[0]["name"])
        self.output_device_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        devices_frame.grid_columnconfigure(1, weight=1)

        # Botões de Controle
        control_frame = ttk.Frame(main_frame, padding="10")
        control_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        self.start_button = ttk.Button(control_frame, text="Iniciar", command=self.start_audio)
        self.start_button.pack(side="left", padx=10)

        self.stop_button = ttk.Button(control_frame, text="Parar", command=self.stop_audio)
        self.stop_button.pack(side="left", padx=10)
        self.stop_button.config(state=tk.DISABLED)

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_audio_devices(self):
        try:
            self.p = pyaudio.PyAudio()
            self.input_devices = self.get_audio_devices(input_only=True)
            self.output_devices = self.get_audio_devices(output_only=True)
        except Exception as e:
            print(f"Erro ao inicializar PyAudio ou carregar dispositivos: {e}")
            self.input_devices = []
            self.output_devices = []
            # Exibir mensagem de erro na GUI se possível

    def get_audio_devices(self, input_only=False, output_only=False):
        devices = []
        if self.p is None:
            return devices

        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get("deviceCount")
        for i in range(num_devices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            if input_only and device_info.get("maxInputChannels") > 0:
                devices.append(device_info)
            elif output_only and device_info.get("maxOutputChannels") > 0:
                devices.append(device_info)
            elif not input_only and not output_only:
                devices.append(device_info)
        return devices

    def audio_callback(self, in_data, frame_count, time_info, status):
        self.buffer.append(in_data)

        try:
            seconds = int(self.seconds_entry.get())
            milliseconds = int(self.milliseconds_entry.get())
            total_delay_ms = (seconds * 1000) + milliseconds
        except ValueError:
            total_delay_ms = 0 # Default to no delay if input is invalid

        delay_frames = int(total_delay_ms / 1000 * self.RATE)

        if len(self.buffer) * self.CHUNK > delay_frames:
            out_data = self.buffer.popleft()
        else:
            out_data = np.zeros(frame_count * self.CHANNELS, dtype=np.int16).tobytes()
        return (out_data, pyaudio.paContinue)

    def start_audio(self):
        if self.running:
            return # Already running

        try:
            self.load_audio_devices() # Recarrega dispositivos para garantir que estejam atualizados

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
                print("Erro: Dispositivo de entrada ou saída não selecionado/encontrado.")
                return

            self.stream = self.p.open(format=self.FORMAT,
                                    channels=self.CHANNELS,
                                    rate=self.RATE,
                                    input=True,
                                    output=True,
                                    input_device_index=input_device_index,
                                    output_device_index=output_device_index,
                                    frames_per_buffer=self.CHUNK,
                                    stream_callback=self.audio_callback)

            self.stream.start_stream()
            self.running = True
            print(f"Áudio iniciado com delay de {self.seconds_entry.get()}s e {self.milliseconds_entry.get()}ms. Entrada: {self.input_device_var.get()}, Saída: {self.output_device_var.get()}")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.set_input_states(tk.DISABLED)

        except Exception as e:
            print(f"Erro ao iniciar áudio: {e}")
            # Exibir mensagem de erro na GUI

    def stop_audio(self):
        if not self.running:
            return # Not running

        try:
            self.running = False
            if self.stream and self.stream.is_active():
                self.stream.stop_stream()
            if self.stream:
                self.stream.close()
            if self.p:
                self.p.terminate()
                self.p = None # Permite re-inicialização
            self.buffer.clear()
            print("Áudio parado.")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.set_input_states(tk.NORMAL)

        except Exception as e:
            print(f"Erro ao parar áudio: {e}")

    def set_input_states(self, state):
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
