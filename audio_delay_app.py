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
        master.title("Rádio Delay Pro") # Novo nome do aplicativo
        master.geometry("800x600") # Aumentando o tamanho da janela para acomodar o novo layout
        master.resizable(False, False) # Desabilitar redimensionamento

        self.p = None # Instância do PyAudio
        self.stream = None
        self.running = False
        self.bypass_active = False # Novo estado para o bypass
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
        style.theme_use("clam") # Tema mais moderno
        style.configure("TFrame", background="#2e2e2e") # Fundo escuro
        style.configure("TLabel", background="#2e2e2e", foreground="#ffffff", font=("Arial", 12))
        style.configure("TButton", font=("Arial", 12, "bold"), padding=10, background="#4a4a4a", foreground="#ffffff")
        style.map("TButton", background=[("active", "#6a6a6a")])
        style.configure("TEntry", font=("Arial", 12), fieldbackground="#4a4a4a", foreground="#ffffff")
        style.configure("TCombobox", font=("Arial", 12), fieldbackground="#4a4a4a", foreground="#ffffff")
        style.configure("TLabelFrame", font=("Arial", 14, "bold"), foreground="#ffffff", background="#2e2e2e")
        # style.configure("TLabelFrame.Label", background="#2e2e2e", foreground="#ffffff") # REMOVIDO

        # Frame principal
        main_frame = ttk.Frame(master, padding="20", style="TFrame")
        main_frame.pack(fill="both", expand=True)

        # Título e Versão
        title_frame = ttk.Frame(main_frame, style="TFrame")
        title_frame.grid(row=0, column=0, columnspan=3, pady=10, sticky="w")

        # Placeholder para o ícone do aplicativo (se houver)
        # self.app_icon = tk.PhotoImage(file="app_icon.png")
        # ttk.Label(title_frame, image=self.app_icon, background="#2e2e2e").pack(side="left", padx=10)

        ttk.Label(title_frame, text="Rádio Delay Pro", font=("Arial", 24, "bold")).pack(side="left", padx=10)
        ttk.Label(title_frame, text="Versão 1.0", font=("Arial", 14)).pack(side="left", pady=5)

        # Slider de Delay (representação visual, não funcional para input)
        self.delay_slider = ttk.Scale(main_frame, from_=0, to=100, orient="horizontal", length=300)
        self.delay_slider.set(0) # Valor inicial
        self.delay_slider.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.delay_value_label = ttk.Label(main_frame, text="0 s", font=("Arial", 14))
        self.delay_value_label.grid(row=1, column=1, padx=5, pady=10, sticky="w")

        # Configurações de Delay (inputs reais)
        delay_input_frame = ttk.LabelFrame(main_frame, text="Configurar Delay", padding="10", style="TLabelFrame")
        delay_input_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(delay_input_frame, text="Minutos:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.minutes_entry = ttk.Entry(delay_input_frame, width=5)
        self.minutes_entry.insert(0, "0")
        self.minutes_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(delay_input_frame, text="Segundos:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.seconds_entry = ttk.Entry(delay_input_frame, width=5)
        self.seconds_entry.insert(0, "0")
        self.seconds_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(delay_input_frame, text="Milissegundos:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.milliseconds_entry = ttk.Entry(delay_input_frame, width=5)
        self.milliseconds_entry.insert(0, "0")
        self.milliseconds_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")

        # Botões de Controle
        control_buttons_frame = ttk.Frame(main_frame, style="TFrame")
        control_buttons_frame.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        self.bypass_button = ttk.Button(control_buttons_frame, text="Bypass", command=self.toggle_bypass, style="TButton")
        self.bypass_button.pack(side="left", padx=5)

        self.start_button = ttk.Button(control_buttons_frame, text="Iniciar", command=self.start_audio, style="TButton")
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(control_buttons_frame, text="Parar", command=self.stop_audio, style="TButton")
        self.stop_button.pack(side="left", padx=5)
        self.stop_button.config(state=tk.DISABLED)

        # VU Meters (placeholders)
        vu_meters_frame = ttk.Frame(main_frame, style="TFrame")
        vu_meters_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ttk.Label(vu_meters_frame, text="Entrada de Áudio", font=("Arial", 12, "bold")).pack(side="left", padx=20)
        self.input_vu = tk.Canvas(vu_meters_frame, width=50, height=100, bg="#4a4a4a", highlightthickness=0)
        self.input_vu.pack(side="left", padx=5)

        ttk.Label(vu_meters_frame, text="Saída de Áudio", font=("Arial", 12, "bold")).pack(side="left", padx=20)
        self.output_vu = tk.Canvas(vu_meters_frame, width=50, height=100, bg="#4a4a4a", highlightthickness=0)
        self.output_vu.pack(side="left", padx=5)

        # Seleção de Dispositivos de Áudio
        devices_frame = ttk.LabelFrame(main_frame, text="Seleção de Dispositivos de Áudio", padding="15", style="TLabelFrame")
        devices_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

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

        # Rodapé
        footer_frame = ttk.Frame(main_frame, style="TFrame")
        footer_frame.grid(row=5, column=0, columnspan=3, pady=10, sticky="se")
        ttk.Label(footer_frame, text="Eng RBS Rádios", font=("Arial", 10)).pack(side="right")

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
            # TODO: Exibir mensagem de erro na GUI

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
        # Atualizar VU meters (simples, apenas para visualização)
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        peak = np.amax(np.abs(audio_data)) / 32768.0 # Normaliza para 0-1
        self.update_vu_meter(self.input_vu, peak)

        if self.bypass_active: # Se bypass ativo, passa o áudio diretamente
            out_data = in_data
        else:
            self.buffer.append(in_data)

            try:
                minutes = int(self.minutes_entry.get())
                seconds = int(self.seconds_entry.get())
                milliseconds = int(self.milliseconds_entry.get())
                total_delay_ms = (minutes * 60 * 1000) + (seconds * 1000) + milliseconds
            except ValueError:
                total_delay_ms = 0 # Default to no delay if input is invalid

            delay_frames = int(total_delay_ms / 1000 * self.RATE)

            if len(self.buffer) * self.CHUNK > delay_frames:
                out_data = self.buffer.popleft()
            else:
                out_data = np.zeros(frame_count * self.CHANNELS, dtype=np.int16).tobytes()
        
        # Atualizar VU meter de saída
        output_audio_data = np.frombuffer(out_data, dtype=np.int16)
        output_peak = np.amax(np.abs(output_audio_data)) / 32768.0
        self.update_vu_meter(self.output_vu, output_peak)

        return (out_data, pyaudio.paContinue)

    def update_vu_meter(self, canvas, peak):
        canvas.delete("all")
        height = canvas.winfo_height()
        width = canvas.winfo_width()
        fill_height = int(height * peak)
        canvas.create_rectangle(0, height - fill_height, width, height, fill="#00ff00", outline="") # Verde
        if peak > 0.6: # Amarelo
            canvas.create_rectangle(0, height - fill_height, width, height * 0.4, fill="#ffff00", outline="")
        if peak > 0.8: # Vermelho
            canvas.create_rectangle(0, height - fill_height, width, height * 0.2, fill="#ff0000", outline="")

    def toggle_bypass(self):
        self.bypass_active = not self.bypass_active
        if self.bypass_active:
            self.bypass_button.config(text="Bypass Ativo", style="TButton.BypassActive")
            self.set_input_states(tk.DISABLED) # Desabilita inputs quando bypass ativo
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)
            if self.running: # Se estiver rodando, para o áudio para limpar o buffer de delay
                self.stop_audio()
            print("Bypass Ativo")
        else:
            self.bypass_button.config(text="Bypass", style="TButton")
            self.set_input_states(tk.NORMAL) # Habilita inputs quando bypass inativo
            self.start_button.config(state=tk.NORMAL)
            print("Bypass Inativo")

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
                # TODO: Exibir mensagem de erro na GUI
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
            print(f"Áudio iniciado com delay de {self.minutes_entry.get()}m {self.seconds_entry.get()}s e {self.milliseconds_entry.get()}ms. Entrada: {self.input_device_var.get()}, Saída: {self.output_device_var.get()}")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.set_input_states(tk.DISABLED)

        except Exception as e:
            print(f"Erro ao iniciar áudio: {e}")
            # TODO: Exibir mensagem de erro na GUI

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
