import tkinter as tk
from tkinter import ttk, messagebox
import pyaudio
import numpy as np
import time
from collections import deque

class AudioDelayApp:
    def __init__(self, master):
        self.master = master
        master.title("Rádio Delay Pro")
        master.geometry("600x450")
        master.resizable(True, True)

        self.p = None
        self.stream = None
        self.running = False
        self.delay_active = False
        self.buffer = deque()

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100

        self.input_devices = []
        self.output_devices = []
        self.input_peak = 0.0
        self.output_peak = 0.0
        self.dark_mode = True
        self.load_audio_devices()

        # Estilo para os widgets
        style = ttk.Style()

        # Criar tema dark (azul mais opaco)
        style.theme_create("dark", parent="default", settings={
            "TFrame": {"configure": {"background": "#0B264E"}},
            "TLabel": {"configure": {"background": "#0B264E", "foreground": "#E6E6FA", "font": ("Segoe UI", 11)}},
            "Title.TLabel": {"configure": {"background": "#0B264E", "foreground": "#E6E6FA", "font": ("Segoe UI", 16, "bold")}},
            "VU.TLabel": {"configure": {"background": "#0B264E", "foreground": "#E6E6FA", "font": ("Segoe UI", 10, "bold")}},
            "Footer.TLabel": {"configure": {"background": "#0B264E", "foreground": "#B0C4DE", "font": ("Segoe UI", 10, "bold")}},
            "Status.TLabel": {"configure": {"background": "#0B264E", "foreground": "#E6E6FA", "font": ("Segoe UI", 10, "italic")}},
            "TButton": {"configure": {"font": ("Segoe UI", 10, "bold"), "padding": 8, "background": "#1940B3", "foreground": "#E6E6FA"},
                        "map": {"background": [("active", "#1B4A70")]}},
            "TEntry": {"configure": {"font": ("Segoe UI", 10), "fieldbackground": "#1940B3", "foreground": "#E6E6FA", "padding": "4 4 4 4"}},
            "TCombobox": {"configure": {"font": ("Segoe UI", 10), "fieldbackground": "#1940B3", "foreground": "#E6E6FA", "padding": "4 4 4 4"}},
            "TLabelframe": {"configure": {"background": "#0B264E", "foreground": "#E6E6FA"}},
            "TLabelframe.Label": {"configure": {"background": "#0B264E", "foreground": "#E6E6FA"}},
        })

        # Criar tema light (bege mais claro)
        style.theme_create("light", parent="default", settings={
            "TFrame": {"configure": {"background": "#B8C6FF"}},
            "TLabel": {"configure": {"background": "#B8C6FF", "foreground": "#333333", "font": ("Segoe UI", 11)}},
            "Title.TLabel": {"configure": {"background": "#B8C6FF", "foreground": "#333333", "font": ("Segoe UI", 16, "bold")}},
            "VU.TLabel": {"configure": {"background": "#B8C6FF", "foreground": "#333333", "font": ("Segoe UI", 10, "bold")}},
            "Footer.TLabel": {"configure": {"background": "#B8C6FF", "foreground": "#555555", "font": ("Segoe UI", 10, "bold")}},
            "Status.TLabel": {"configure": {"background": "#B8C6FF", "foreground": "#333333", "font": ("Segoe UI", 10, "italic")}},
            "TButton": {"configure": {"font": ("Segoe UI", 10, "bold"), "padding": 8, "background": "#D3D3D3", "foreground": "#333333"},
                        "map": {"background": [("active", "#C0C0C0")]}},
            "TEntry": {"configure": {"font": ("Segoe UI", 10), "fieldbackground": "#FFFFFF", "foreground": "#333333", "padding": "4 4 4 4"}},
            "TCombobox": {"configure": {"font": ("Segoe UI", 10), "fieldbackground": "#FFFFFF", "foreground": "#333333", "padding": "4 4 4 4"}},
            "TLabelframe": {"configure": {"background": "#B8C6FF", "foreground": "#333333"}},
            "TLabelframe.Label": {"configure": {"background": "#B8C6FF", "foreground": "#333333"}},
        })

        style.theme_use("dark")

        # Frame principal com grid para responsividade
        master.grid_rowconfigure(0, weight=1)
        master.grid_rowconfigure(1, weight=0)
        master.grid_columnconfigure(0, weight=1)

        main_frame = ttk.Frame(master, style="TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(0, weight=0)
        main_frame.grid_rowconfigure(1, weight=0)
        main_frame.grid_rowconfigure(2, weight=0)
        main_frame.grid_rowconfigure(3, weight=0)
        main_frame.grid_rowconfigure(4, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        # Header frame com título e botão de modo
        header_frame = ttk.Frame(main_frame, style="TFrame")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 5))

        ttk.Label(header_frame, text="Rádio Delay Pro", style="Title.TLabel").pack(side="left", padx=10)
        self.toggle_mode_button = ttk.Button(header_frame, text="Alternar Modo", command=self.toggle_mode)
        self.toggle_mode_button.pack(side="right", padx=10)

        # Configurações de Delay (esquerda) e Dispositivos (direita)
        config_frame = ttk.Frame(main_frame, style="TFrame")
        config_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=5)
        config_frame.grid_columnconfigure(0, weight=1)
        config_frame.grid_columnconfigure(1, weight=1)

        # Configurações de Delay
        delay_frame = ttk.LabelFrame(config_frame, text="Configurar Delay", padding="5", style="TLabelframe")
        delay_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        
        ttk.Label(delay_frame, text="Minutos:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.minutes_entry = ttk.Entry(delay_frame, width=8)
        self.minutes_entry.insert(0, "0")
        self.minutes_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(delay_frame, text="Segundos:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.seconds_entry = ttk.Entry(delay_frame, width=8)
        self.seconds_entry.insert(0, "0")
        self.seconds_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(delay_frame, text="Milissegundos:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.milliseconds_entry = ttk.Entry(delay_frame, width=8)
        self.milliseconds_entry.insert(0, "0")
        self.milliseconds_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        delay_frame.grid_columnconfigure(1, weight=1)

        # Seleção de Dispositivos de Áudio
        devices_frame = ttk.LabelFrame(config_frame, text="Dispositivos de Áudio", padding="5", style="TLabelframe")
        devices_frame.grid(row=0, column=1, sticky="nsew", padx=5)

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
        control_buttons_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

        self.start_button = ttk.Button(control_buttons_frame, text="Iniciar", command=self.start_audio)
        self.start_button.pack(side="left", padx=10, fill="x", expand=True)

        self.stop_button = ttk.Button(control_buttons_frame, text="Parar", command=self.stop_audio)
        self.stop_button.pack(side="left", padx=10, fill="x", expand=True)
        self.stop_button.pack_forget()

        self.bypass_button = ttk.Button(control_buttons_frame, text="Bypass", command=self.toggle_bypass)
        self.bypass_button.pack(side="left", padx=10, fill="x", expand=True)

        # Status Label
        self.status_label = ttk.Label(main_frame, text="Pronto", style="Status.TLabel")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")

        # VU Meters
        vu_meters_frame = ttk.Frame(main_frame, style="TFrame")
        vu_meters_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=5)

        vu_input_frame = ttk.Frame(vu_meters_frame, style="TFrame")
        vu_input_frame.pack(fill="x", pady=2)
        ttk.Label(vu_input_frame, text="Entrada:", style="VU.TLabel").pack(side="left", padx=5)
        self.input_vu = tk.Canvas(vu_input_frame, width=150, height=15, bg="#4169E1" if self.dark_mode else "#D3D3D3", highlightthickness=0)
        self.input_vu.pack(side="left", fill="x", expand=True, padx=5)

        vu_output_frame = ttk.Frame(vu_meters_frame, style="TFrame")
        vu_output_frame.pack(fill="x", pady=2)
        ttk.Label(vu_output_frame, text="Saída:", style="VU.TLabel").pack(side="left", padx=5)
        self.output_vu = tk.Canvas(vu_output_frame, width=150, height=15, bg="#4169E1" if self.dark_mode else "#D3D3D3", highlightthickness=0)
        self.output_vu.pack(side="left", fill="x", expand=True, padx=5)

        # Rodapé fixo
        footer_frame = ttk.Frame(master, style="TFrame")
        footer_frame.grid(row=1, column=0, sticky="sew")
        ttk.Label(footer_frame, text="© Eng RBS Rádios by Maiko Costa - Versão 2.0", style="Footer.TLabel", anchor="e").pack(fill="x", padx=10)

        master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.set_initial_state()

    def toggle_mode(self):
        self.dark_mode = not self.dark_mode
        style = ttk.Style()
        style.theme_use("dark" if self.dark_mode else "light")
        vu_bg = "#4169E1" if self.dark_mode else "#D3D3D3"
        self.input_vu.config(bg=vu_bg)
        self.output_vu.config(bg=vu_bg)

    def set_initial_state(self):
        self.set_input_states(tk.NORMAL)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.pack_forget()
        self.bypass_button.config(state=tk.NORMAL, text="Bypass")
        self.delay_active = False
        self.status_label.config(text="Pronto")

    def load_audio_devices(self):
        try:
            self.p = pyaudio.PyAudio()
            self.input_devices = self.get_audio_devices(input_only=True)
            self.output_devices = self.get_audio_devices(output_only=True)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao inicializar PyAudio ou carregar dispositivos: {e}")
            self.input_devices = []
            self.output_devices = []

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
        try:
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            peak = np.amax(np.abs(audio_data)) / 32768.0
            self.input_peak = peak

            out_data = in_data

            if self.delay_active:
                self.buffer.append(in_data)
                try:
                    minutes = int(self.minutes_entry.get() or "0")
                    seconds = int(self.seconds_entry.get() or "0")
                    milliseconds = int(self.milliseconds_entry.get() or "0")
                    total_delay_ms = (minutes * 60 * 1000) + (seconds * 1000) + milliseconds
                except ValueError:
                    total_delay_ms = 0

                delay_frames = int(total_delay_ms / 1000 * self.RATE)
                delay_chunks = delay_frames // self.CHUNK + (1 if delay_frames % self.CHUNK else 0)

                if len(self.buffer) > delay_chunks:
                    out_data = self.buffer.popleft()
                else:
                    out_data = np.zeros(frame_count * self.CHANNELS, dtype=np.int16).tobytes()

            output_audio_data = np.frombuffer(out_data, dtype=np.int16)
            output_peak = np.amax(np.abs(output_audio_data)) / 32768.0
            self.output_peak = output_peak

            return (out_data, pyaudio.paContinue)
        except Exception as e:
            print(f"Erro no callback: {e}")
            return (np.zeros(frame_count * self.CHANNELS, dtype=np.int16).tobytes(), pyaudio.paContinue)

    def update_vu_meter(self, canvas, peak):
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        fill_width = int(width * peak)

        num_steps = fill_width
        for i in range(num_steps):
            ratio = i / width
            if ratio < 0.6:
                r = int(255 * (ratio / 0.6))
                g = 255
                b = 0
            else:
                r = 255
                g = int(255 * (1 - (ratio - 0.6) / 0.4))
                b = 0
            color = f'#{r:02x}{g:02x}{b:02x}'
            canvas.create_line(i, 0, i, height, fill=color)

    def update_vu_loop(self):
        self.update_vu_meter(self.input_vu, self.input_peak)
        self.update_vu_meter(self.output_vu, self.output_peak)
        if self.running:
            self.master.after(50, self.update_vu_loop)

    def toggle_bypass(self):
        if not self.running:
            return

        if self.delay_active:
            self.delay_active = False
            self.bypass_button.config(text="Bypass Ativo")
            self.status_label.config(text="Executando em modo Bypass")
            print("Modo Bypass Ativado.")
        else:
            self.delay_active = True
            self.bypass_button.config(text="Delay Ativo")
            self.status_label.config(text="Executando com Delay")
            print("Modo Delay Ativado.")

    def start_audio(self):
        if self.running:
            return

        self.delay_active = False
        self.buffer.clear()

        try:
            self.load_audio_devices()

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
                messagebox.showerror("Erro", "Dispositivo de entrada ou saída não selecionado/encontrado.")
                return

            self._safe_close_stream()

            self.p = pyaudio.PyAudio()

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
            print(f"Áudio iniciado em modo Bypass. Entrada: {self.input_device_var.get()}, Saída: {self.output_device_var.get()}")

            self.update_vu_loop()

            self.start_button.config(state=tk.DISABLED)
            self.stop_button.pack(side="left", padx=10, fill="x", expand=True)
            self.stop_button.config(state=tk.NORMAL)
            self.bypass_button.config(text="Bypass Ativo", state=tk.NORMAL)
            # Keep delay input fields enabled to allow real-time adjustments
            self.input_device_dropdown.config(state=tk.DISABLED)
            self.output_device_dropdown.config(state=tk.DISABLED)
            self.status_label.config(text="Executando em modo Bypass")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar áudio: {e}")
            self._safe_close_stream()

    def stop_audio(self):
        if not self.running:
            return

        try:
            self.running = False
            self._safe_close_stream()
            self.buffer.clear()
            print("Áudio parado.")

            self.set_initial_state()

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao parar áudio: {e}")

    def _safe_close_stream(self):
        if self.stream is not None:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Erro ao fechar stream: {e}")
            finally:
                self.stream = None
        if self.p is not None:
            try:
                self.p.terminate()
            except Exception as e:
                print(f"Erro ao terminar PyAudio: {e}")
            finally:
                self.p = None

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
    try:
        root.iconbitmap("mic.ico")
    except tk.TclError:
        pass
    app = AudioDelayApp(root)
    root.mainloop()