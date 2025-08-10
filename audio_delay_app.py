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
        master.resizable(False, False)

        self.p = None
        self.stream = None
        self.running = False
        self.delay_active = False  # True if delay is applied, False if bypass
        self.buffer = deque()

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100

        self.input_devices = []
        self.output_devices = []
        self.input_peak = 0.0
        self.output_peak = 0.0
        self.load_audio_devices()

        # Estilo para os widgets
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TFrame", background="#2e2e2e")
        style.configure("TLabel", background="#2e2e2e", foreground="#ffffff", font=("Arial", 11))
        style.configure("TButton", font=("Arial", 11, "bold"), padding=8, background="#4a4a4a", foreground="#ffffff")
        style.map("TButton", background=[("active", "#6a6a6a")])
        style.configure("TEntry", font=("Arial", 11), fieldbackground="#4a4a4a", foreground="#ffffff")
        style.configure("TCombobox", font=("Arial", 11), fieldbackground="#4a4a4a", foreground="#ffffff")

        # Frame principal
        main_frame = ttk.Frame(master, padding="15", style="TFrame")
        main_frame.pack(fill="both", expand=True)

        # Título
        title_frame = ttk.Frame(main_frame, style="TFrame")
        title_frame.pack(pady=10)

        ttk.Label(title_frame, text="Rádio Delay Pro", font=("Arial", 20, "bold")).pack()

        # Configurações de Delay
        delay_frame = ttk.LabelFrame(main_frame, text="Configurar Delay", padding="10")
        delay_frame.pack(pady=10, padx=10, fill="x")

        delay_input_subframe = ttk.Frame(delay_frame, style="TFrame")
        delay_input_subframe.pack(pady=5)

        ttk.Label(delay_input_subframe, text="Minutos:").grid(row=0, column=0, padx=5, pady=2)
        self.minutes_entry = ttk.Entry(delay_input_subframe, width=5)
        self.minutes_entry.insert(0, "0")
        self.minutes_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(delay_input_subframe, text="Segundos:").grid(row=0, column=2, padx=5, pady=2)
        self.seconds_entry = ttk.Entry(delay_input_subframe, width=5)
        self.seconds_entry.insert(0, "0")
        self.seconds_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(delay_input_subframe, text="Milissegundos:").grid(row=0, column=4, padx=5, pady=2)
        self.milliseconds_entry = ttk.Entry(delay_input_subframe, width=5)
        self.milliseconds_entry.insert(0, "0")
        self.milliseconds_entry.grid(row=0, column=5, padx=5, pady=2)

        # Seleção de Dispositivos de Áudio
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
        control_buttons_frame.pack(pady=15)

        self.start_button = ttk.Button(control_buttons_frame, text="Iniciar", command=self.start_audio, style="TButton")
        self.start_button.pack(side="left", padx=15)

        self.stop_button = ttk.Button(control_buttons_frame, text="Parar", command=self.stop_audio, style="TButton")
        self.stop_button.pack(side="left", padx=15)
        self.stop_button.pack_forget()  # Ocultar inicialmente

        self.bypass_button = ttk.Button(control_buttons_frame, text="Bypass", command=self.toggle_bypass, style="TButton")
        self.bypass_button.pack(side="left", padx=15)

        # Status Label
        self.status_label = ttk.Label(main_frame, text="Pronto", font=("Arial", 12, "italic"), background="#2e2e2e", foreground="#ffffff")
        self.status_label.pack(pady=10)

        # VU Meters (simplificados, mais altos para melhor visualização)
        vu_meters_frame = ttk.Frame(main_frame, style="TFrame")
        vu_meters_frame.pack(pady=10)

        ttk.Label(vu_meters_frame, text="Entrada:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.input_vu = tk.Canvas(vu_meters_frame, width=20, height=120, bg="#4a4a4a", highlightthickness=0)
        self.input_vu.pack(side="left", padx=5)

        ttk.Label(vu_meters_frame, text="Saída:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.output_vu = tk.Canvas(vu_meters_frame, width=20, height=120, bg="#4a4a4a", highlightthickness=0)
        self.output_vu.pack(side="left", padx=5)

        # Rodapé com informações atualizadas
        footer_frame = ttk.Frame(master, style="TFrame")
        footer_frame.pack(side="bottom", fill="x", pady=5)
        ttk.Label(footer_frame, text="© Eng RBS Rádios by Maiko Costa versão 1.5", font=("Arial", 9), anchor="e").pack(fill="x", padx=10)

        master.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configura o estado inicial dos inputs e botões
        self.set_initial_state()

    def set_initial_state(self):
        self.set_input_states(tk.NORMAL)
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.pack_forget()
        self.bypass_button.config(state=tk.NORMAL, text="Bypass")
        self.delay_active = False  # Start in bypass mode conceptually
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
            # Atualizar picos para VU meters
            audio_data = np.frombuffer(in_data, dtype=np.int16)
            peak = np.amax(np.abs(audio_data)) / 32768.0  # Normaliza para 0-1
            self.input_peak = peak

            out_data = in_data  # Por padrão, áudio passa direto (bypass)

            if self.delay_active:  # Se o delay estiver ativo
                self.buffer.append(in_data)

                try:
                    minutes = int(self.minutes_entry.get())
                    seconds = int(self.seconds_entry.get())
                    milliseconds = int(self.milliseconds_entry.get())
                    total_delay_ms = (minutes * 60 * 1000) + (seconds * 1000) + milliseconds
                except ValueError:
                    total_delay_ms = 0  # Default to no delay if input is invalid

                delay_frames = int(total_delay_ms / 1000 * self.RATE)
                delay_chunks = delay_frames // self.CHUNK + (1 if delay_frames % self.CHUNK else 0)

                if len(self.buffer) > delay_chunks:
                    out_data = self.buffer.popleft()
                else:
                    out_data = np.zeros(frame_count * self.CHANNELS, dtype=np.int16).tobytes()

            # Atualizar pico de saída
            output_audio_data = np.frombuffer(out_data, dtype=np.int16)
            output_peak = np.amax(np.abs(output_audio_data)) / 32768.0
            self.output_peak = output_peak

            return (out_data, pyaudio.paContinue)
        except Exception as e:
            print(f"Erro no callback: {e}")
            return (np.zeros(frame_count * self.CHANNELS, dtype=np.int16).tobytes(), pyaudio.paContinue)

    def update_vu_meter(self, canvas, peak):
        canvas.delete("all")
        height = canvas.winfo_height()
        width = canvas.winfo_width()

        # Desenhar seção verde (0-60%)
        green_height = min(peak, 0.6) * height
        canvas.create_rectangle(0, height - green_height, width, height, fill="#00ff00", outline="")

        # Desenhar seção amarela (60-80%)
        if peak > 0.6:
            yellow_height = min(peak - 0.6, 0.2) * height
            canvas.create_rectangle(0, height - green_height - yellow_height, width, height - green_height, fill="#ffff00", outline="")

        # Desenhar seção vermelha (80-100%)
        if peak > 0.8:
            red_height = (peak - 0.8) * height
            canvas.create_rectangle(0, height - green_height - (0.2 * height) - red_height, width, height - green_height - (0.2 * height), fill="#ff0000", outline="")

    def update_vu_loop(self):
        self.update_vu_meter(self.input_vu, self.input_peak)
        self.update_vu_meter(self.output_vu, self.output_peak)
        if self.running:
            self.master.after(50, self.update_vu_loop)

    def toggle_bypass(self):
        if not self.running:  # Se não estiver rodando, não faz nada
            return

        if self.delay_active:  # Se estiver com delay, muda para bypass
            self.delay_active = False
            self.bypass_button.config(text="Bypass Ativo")
            self.status_label.config(text="Executando em modo Bypass")
            print("Modo Bypass Ativado.")
        else:  # Se estiver em bypass, muda para delay
            self.delay_active = True
            self.bypass_button.config(text="Delay Ativo")
            self.status_label.config(text="Executando com Delay")
            print("Modo Delay Ativado.")

    def start_audio(self):
        if self.running:
            return  # Já está rodando

        self.delay_active = False  # Inicia em bypass por padrão ao clicar em Iniciar
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

            # Fechar qualquer stream existente de forma segura
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

            # Iniciar loop de atualização dos VU meters
            self.update_vu_loop()

            # Atualiza o estado dos botões e status
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.pack(side="left", padx=15)  # Mostra o botão Parar
            self.stop_button.config(state=tk.NORMAL)
            self.bypass_button.config(text="Bypass Ativo", state=tk.NORMAL)
            self.set_input_states(tk.DISABLED)
            self.status_label.config(text="Executando em modo Bypass")

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar áudio: {e}")
            self._safe_close_stream()

    def stop_audio(self):
        if not self.running:
            return  # Não está rodando

        try:
            self.running = False
            self._safe_close_stream()
            self.buffer.clear()
            print("Áudio parado.")

            # Reseta o estado dos botões para o padrão inicial
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
        pass  # Ícone não encontrado, ignora silenciosamente
    app = AudioDelayApp(root)
    root.mainloop()