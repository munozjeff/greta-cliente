#!/usr/bin/env python3
"""
cliente_gui.py — App cliente de prueba para Greta Server
=========================================================
Interfaz gráfica que permite:
  • Conectarse al servidor (local o internet vía ngrok)
  • Enviar mensajes y ver la respuesta
  • Simular múltiples clientes enviando al mismo tiempo (para probar la cola)
  • Ver el historial de respuestas en tiempo real
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import requests
import json
import time
from datetime import datetime
import queue as queue_module

# ============================================================
# CONFIGURACIÓN POR DEFECTO
# ============================================================

DEFAULT_URL    = "http://localhost:8000"
DEFAULT_APIKEY = "greta-test-2024"
DEFAULT_NOMBRE = "Cliente-1"

# ============================================================
# COLORES Y ESTILOS (tema oscuro)
# ============================================================

C = {
    "bg":         "#0f1117",
    "bg_card":    "#1a1d27",
    "bg_input":   "#252836",
    "bg_panel":   "#12151e",
    "accent":     "#6366f1",       # violeta índigo
    "accent2":    "#22d3ee",       # cian
    "success":    "#22c55e",       # verde
    "warning":    "#f59e0b",       # ámbar
    "error":      "#ef4444",       # rojo
    "text":       "#e2e8f0",
    "text_dim":   "#64748b",
    "text_mid":   "#94a3b8",
    "border":     "#2d3148",
    "tag_send":   "#6366f1",
    "tag_recv":   "#22c55e",
    "tag_err":    "#ef4444",
    "tag_sys":    "#64748b",
    "tag_queue":  "#f59e0b",
}

FONT_MONO  = ("Consolas", 10)
FONT_LABEL = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI Semibold", 10)
FONT_BIG   = ("Segoe UI Semibold", 13)
FONT_TITLE = ("Segoe UI Bold", 15)


# ============================================================
# LÓGICA DE COMUNICACIÓN (en threads separados)
# ============================================================

class GretaClient:
    """Maneja la comunicación HTTP con el servidor."""

    def __init__(self, url: str, api_key: str, cliente_id: str):
        self.url       = url.rstrip("/")
        self.api_key   = api_key
        self.cliente_id = cliente_id
        self.headers   = {
            "X-API-Key":    api_key,
            "Content-Type": "application/json",
        }
        self.timeout = 150

    def health(self) -> dict:
        r = requests.get(f"{self.url}/health", timeout=10)
        r.raise_for_status()
        return r.json()

    def cola(self) -> dict:
        r = requests.get(f"{self.url}/cola", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def enviar(self, mensaje: str, parametros: dict = {}) -> dict:
        payload = {
            "mensaje":    mensaje,
            "cliente_id": self.cliente_id,
            "parametros": parametros,
        }
        r = requests.post(
            f"{self.url}/mensaje",
            headers=self.headers,
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()


# ============================================================
# VENTANA PRINCIPAL
# ============================================================

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Greta Server — Cliente de Prueba")
        self.geometry("920x700")
        self.minsize(780, 580)
        self.configure(bg=C["bg"])

        # Estado
        self.client: GretaClient | None = None
        self._log_queue = queue_module.Queue()
        self._enviando  = False
        self._contador  = 0   # contador de mensajes enviados

        self._build_ui()
        self._process_log_queue()

        # Chequeo periódico de la cola del servidor
        self._poll_server()

    # ─────────────────────────────────────────────────────────
    # UI
    # ─────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_connection_panel()
        self._build_main_area()
        self._build_status_bar()

    def _build_header(self):
        hdr = tk.Frame(self, bg="#0d0f18", pady=12)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="⬡  GRETA SERVER", font=FONT_TITLE,
            bg="#0d0f18", fg=C["accent"]
        ).pack(side="left", padx=20)

        tk.Label(
            hdr, text="Cliente de Prueba · Cola + Long-polling", font=FONT_LABEL,
            bg="#0d0f18", fg=C["text_dim"]
        ).pack(side="left", padx=4)

        # Indicador de conexión
        self.lbl_conn_dot = tk.Label(
            hdr, text="●", font=("Segoe UI", 14),
            bg="#0d0f18", fg=C["error"]
        )
        self.lbl_conn_dot.pack(side="right", padx=4)
        self.lbl_conn_text = tk.Label(
            hdr, text="Desconectado", font=FONT_LABEL,
            bg="#0d0f18", fg=C["text_dim"]
        )
        self.lbl_conn_text.pack(side="right", padx=4)

    def _build_connection_panel(self):
        """Panel de configuración de conexión."""
        pnl = tk.Frame(self, bg=C["bg_card"], pady=10, padx=16)
        pnl.pack(fill="x", padx=14, pady=(10, 4))

        # Fila 1: URL + API Key
        row1 = tk.Frame(pnl, bg=C["bg_card"])
        row1.pack(fill="x", pady=(0, 8))

        # URL
        tk.Label(row1, text="URL Servidor", font=FONT_BOLD, bg=C["bg_card"], fg=C["text_mid"]).pack(side="left")
        self.ent_url = tk.Entry(
            row1, width=36, font=FONT_MONO,
            bg=C["bg_input"], fg=C["text"], insertbackground=C["accent"],
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=C["border"], highlightcolor=C["accent"]
        )
        self.ent_url.insert(0, DEFAULT_URL)
        self.ent_url.pack(side="left", padx=(8, 20), ipady=5, ipadx=4)

        # API Key
        tk.Label(row1, text="API Key", font=FONT_BOLD, bg=C["bg_card"], fg=C["text_mid"]).pack(side="left")
        self.ent_apikey = tk.Entry(
            row1, width=24, font=FONT_MONO,
            bg=C["bg_input"], fg=C["text"], insertbackground=C["accent"],
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=C["border"], highlightcolor=C["accent"],
            show="•"
        )
        self.ent_apikey.insert(0, DEFAULT_APIKEY)
        self.ent_apikey.pack(side="left", padx=(8, 16), ipady=5, ipadx=4)

        # Mostrar/ocultar API Key
        self.btn_show_key = tk.Button(
            row1, text="👁", font=("Segoe UI", 10),
            bg=C["bg_input"], fg=C["text_mid"],
            relief="flat", bd=0, cursor="hand2",
            command=self._toggle_show_key
        )
        self.btn_show_key.pack(side="left")

        # Fila 2: Nombre + Conectar
        row2 = tk.Frame(pnl, bg=C["bg_card"])
        row2.pack(fill="x")

        tk.Label(row2, text="Mi nombre", font=FONT_BOLD, bg=C["bg_card"], fg=C["text_mid"]).pack(side="left")
        self.ent_nombre = tk.Entry(
            row2, width=16, font=FONT_MONO,
            bg=C["bg_input"], fg=C["text"], insertbackground=C["accent"],
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=C["border"], highlightcolor=C["accent"]
        )
        self.ent_nombre.insert(0, DEFAULT_NOMBRE)
        self.ent_nombre.pack(side="left", padx=(8, 16), ipady=5, ipadx=4)

        self.btn_connect = tk.Button(
            row2, text="  Conectar  ", font=FONT_BOLD,
            bg=C["accent"], fg="white",
            relief="flat", bd=0, cursor="hand2", padx=10, pady=4,
            command=self._conectar
        )
        self.btn_connect.pack(side="left", padx=(0, 8))

        self.btn_disconnect = tk.Button(
            row2, text="Desconectar", font=FONT_BOLD,
            bg=C["bg_input"], fg=C["text_dim"],
            relief="flat", bd=0, cursor="hand2", padx=10, pady=4,
            state="disabled",
            command=self._desconectar
        )
        self.btn_disconnect.pack(side="left")

        # Cola badge
        self.lbl_cola = tk.Label(
            row2, text="Cola: —", font=FONT_BOLD,
            bg=C["bg_card"], fg=C["text_dim"]
        )
        self.lbl_cola.pack(side="right", padx=8)

    def _build_main_area(self):
        """Área principal: log + entrada de mensaje."""
        container = tk.Frame(self, bg=C["bg"])
        container.pack(fill="both", expand=True, padx=14, pady=4)

        # ── Log de mensajes ──
        log_frame = tk.Frame(container, bg=C["bg_panel"], bd=0)
        log_frame.pack(fill="both", expand=True)

        tk.Label(
            log_frame, text="  Registro de mensajes", font=FONT_BOLD,
            bg="#0d1020", fg=C["text_mid"], anchor="w", pady=6
        ).pack(fill="x")

        self.txt_log = scrolledtext.ScrolledText(
            log_frame,
            font=FONT_MONO, bg=C["bg_panel"], fg=C["text"],
            relief="flat", bd=0, padx=10, pady=6,
            state="disabled", wrap="word",
            insertbackground=C["accent"],
        )
        self.txt_log.pack(fill="both", expand=True)

        # Configurar colores de tags
        self.txt_log.tag_config("SEND",  foreground=C["tag_send"])
        self.txt_log.tag_config("RECV",  foreground=C["tag_recv"])
        self.txt_log.tag_config("ERROR", foreground=C["tag_err"])
        self.txt_log.tag_config("SYS",   foreground=C["tag_sys"])
        self.txt_log.tag_config("QUEUE", foreground=C["tag_queue"])
        self.txt_log.tag_config("TIME",  foreground=C["text_dim"])
        self.txt_log.tag_config("BOLD",  font=("Consolas", 10, "bold"))

        # ── Panel de entrada ──
        input_frame = tk.Frame(self, bg=C["bg_card"], pady=10, padx=16)
        input_frame.pack(fill="x", padx=14, pady=(4, 6))

        tk.Label(
            input_frame, text="Mensaje a enviar", font=FONT_BOLD,
            bg=C["bg_card"], fg=C["text_mid"]
        ).pack(anchor="w")

        inp_row = tk.Frame(input_frame, bg=C["bg_card"])
        inp_row.pack(fill="x", pady=(6, 0))

        self.ent_mensaje = tk.Entry(
            inp_row, font=("Segoe UI", 12),
            bg=C["bg_input"], fg=C["text"], insertbackground=C["accent"],
            relief="flat", bd=0, highlightthickness=2,
            highlightbackground=C["border"], highlightcolor=C["accent"]
        )
        self.ent_mensaje.pack(side="left", fill="x", expand=True, ipady=8, ipadx=8)
        self.ent_mensaje.bind("<Return>", lambda e: self._enviar())
        self.ent_mensaje.bind("<KP_Enter>", lambda e: self._enviar())

        self.btn_enviar = tk.Button(
            inp_row, text="  Enviar ▶  ", font=FONT_BOLD,
            bg=C["accent"], fg="white",
            relief="flat", bd=0, cursor="hand2", padx=16, pady=8,
            state="disabled",
            command=self._enviar
        )
        self.btn_enviar.pack(side="left", padx=(10, 0))

        # Botón multi-cliente
        self.btn_multi = tk.Button(
            inp_row, text="⚡ x5 clientes", font=FONT_BOLD,
            bg="#1e293b", fg=C["accent2"],
            relief="flat", bd=0, cursor="hand2", padx=12, pady=8,
            state="disabled",
            command=self._enviar_multi
        )
        self.btn_multi.pack(side="left", padx=(8, 0))

        # Botón limpiar log
        tk.Button(
            inp_row, text="🗑", font=("Segoe UI", 12),
            bg=C["bg_card"], fg=C["text_dim"],
            relief="flat", bd=0, cursor="hand2", padx=6,
            command=self._limpiar_log
        ).pack(side="left", padx=(8, 0))

    def _build_status_bar(self):
        bar = tk.Frame(self, bg="#080a10", pady=4)
        bar.pack(fill="x", side="bottom")
        self.lbl_status = tk.Label(
            bar, text="Ingresa la URL del servidor y haz clic en Conectar.",
            font=("Segoe UI", 9), bg="#080a10", fg=C["text_dim"], anchor="w"
        )
        self.lbl_status.pack(side="left", padx=16)

    # ─────────────────────────────────────────────────────────
    # LÓGICA
    # ─────────────────────────────────────────────────────────

    def _toggle_show_key(self):
        current = self.ent_apikey.cget("show")
        self.ent_apikey.config(show="" if current == "•" else "•")

    def _conectar(self):
        url    = self.ent_url.get().strip()
        apikey = self.ent_apikey.get().strip()
        nombre = self.ent_nombre.get().strip() or "Cliente"

        if not url:
            messagebox.showwarning("Faltan datos", "Ingresa la URL del servidor.")
            return

        self._set_status("Conectando...")
        self._log_sys(f"Conectando a {url} ...")

        def _do():
            try:
                self.client = GretaClient(url, apikey, nombre)
                data = self.client.health()
                self._log_queue.put(("SYS_OK", data))
            except Exception as e:
                self._log_queue.put(("SYS_ERR", str(e)))

        threading.Thread(target=_do, daemon=True).start()

    def _desconectar(self):
        self.client = None
        self._set_connected(False)
        self._log_sys("Desconectado del servidor.")

    def _enviar(self):
        if not self.client or self._enviando:
            return
        msg = self.ent_mensaje.get().strip()
        if not msg:
            self.ent_mensaje.focus()
            return

        self._contador += 1
        nombre = self.ent_nombre.get().strip() or "Cliente"
        self._enviar_en_thread(msg, nombre, self._contador)
        self.ent_mensaje.delete(0, "end")

    def _enviar_multi(self):
        """Simula 5 clientes enviando al mismo tiempo."""
        if not self.client:
            return
        msg_base = self.ent_mensaje.get().strip() or "Test multi-cliente"
        self._log_sys(f"⚡ Lanzando 5 clientes simultáneos...")

        for i in range(1, 6):
            nombre = f"Bot-{i}"
            msg    = f"{msg_base} [de {nombre}]"
            self._contador += 1
            t = threading.Thread(
                target=self._enviar_en_thread,
                args=(msg, nombre, self._contador),
                daemon=True
            )
            t.start()
            time.sleep(0.05)  # pequeño intervalo para que el orden sea visible

    def _enviar_en_thread(self, mensaje: str, nombre: str, num: int):
        """Envía un mensaje al servidor en un thread separado."""
        t0 = time.time()
        tag_num = f"#{num}"

        self._log_queue.put(("SEND", nombre, tag_num, mensaje))

        try:
            # Crear client temporal con el nombre correcto
            c = GretaClient(
                self.client.url,
                self.client.api_key,
                nombre
            )
            resultado = c.enviar(mensaje)
            elapsed = round(time.time() - t0, 2)
            self._log_queue.put(("RECV", nombre, tag_num, resultado, elapsed))
        except requests.exceptions.Timeout:
            self._log_queue.put(("ERROR", nombre, tag_num, "Timeout: el servidor no respondió a tiempo."))
        except requests.exceptions.ConnectionError:
            self._log_queue.put(("ERROR", nombre, tag_num, "Error de conexión. ¿El servidor está activo?"))
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            self._log_queue.put(("ERROR", nombre, tag_num, f"HTTP {e.response.status_code}: {detail}"))
        except Exception as e:
            self._log_queue.put(("ERROR", nombre, tag_num, str(e)))

    # ─────────────────────────────────────────────────────────
    # LOG (thread-safe vía queue)
    # ─────────────────────────────────────────────────────────

    def _process_log_queue(self):
        """Procesa mensajes del log desde el thread principal."""
        try:
            while True:
                item = self._log_queue.get_nowait()
                self._handle_log_item(item)
        except queue_module.Empty:
            pass
        self.after(80, self._process_log_queue)

    def _handle_log_item(self, item):
        kind = item[0]

        if kind == "SYS_OK":
            data = item[1]
            self._set_connected(True)
            self._log_sys(
                f"✔ Conectado | Cola actual: {data.get('cola', '?')} | "
                f"Jobs: {data.get('jobs_activos', '?')}"
            )
            self._set_status(f"Conectado a {self.client.url}")

        elif kind == "SYS_ERR":
            self._log_err(f"✘ No se pudo conectar: {item[1]}")
            self._set_status(f"Error de conexión")
            self.client = None

        elif kind == "SEND":
            _, nombre, tag_num, mensaje = item
            self._log_append(
                f"[{self._ts()}] ",  "TIME",
                f"▶ {nombre} {tag_num}  ", "SEND",
                f"→ \"{mensaje}\"\n", "BOLD"
            )

        elif kind == "RECV":
            _, nombre, tag_num, resultado, elapsed = item
            eco = resultado.get("resultado", {}).get("echo", "—")
            demora = resultado.get("resultado", {}).get("demora_s", "?")
            self._log_append(
                f"[{self._ts()}] ",  "TIME",
                f"◀ {nombre} {tag_num}  ", "RECV",
                f"← \"{eco}\"  ", "BOLD",
                f"(procesado en {demora}s | total {elapsed}s)\n", "TIME"
            )

        elif kind == "ERROR":
            _, nombre, tag_num, error = item
            self._log_append(
                f"[{self._ts()}] ",  "TIME",
                f"✘ {nombre} {tag_num}  ", "ERROR",
                f"{error}\n", "ERROR"
            )

        elif kind == "COLA":
            cola_data = item[1]
            pendientes = cola_data.get("pendientes_en_cola", 0)
            activos    = cola_data.get("jobs_activos_total", 0)
            self.lbl_cola.config(
                text=f"Cola: {pendientes} pend | {activos} activos",
                fg=C["warning"] if pendientes > 0 else C["text_mid"]
            )

    def _log_append(self, *parts):
        """Escribe en el log con múltiples segmentos (texto, tag, texto, tag...)"""
        self.txt_log.config(state="normal")
        for i in range(0, len(parts), 2):
            text = parts[i]
            tag  = parts[i+1] if i+1 < len(parts) else "SYS"
            self.txt_log.insert("end", text, tag)
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def _log_sys(self, msg: str):
        self._log_append(f"[{self._ts()}] ", "TIME", f"{msg}\n", "SYS")

    def _log_err(self, msg: str):
        self._log_append(f"[{self._ts()}] ", "TIME", f"{msg}\n", "ERROR")

    def _limpiar_log(self):
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.config(state="disabled")

    def _ts(self):
        return datetime.now().strftime("%H:%M:%S")

    # ─────────────────────────────────────────────────────────
    # ESTADO
    # ─────────────────────────────────────────────────────────

    def _set_connected(self, connected: bool):
        if connected:
            self.lbl_conn_dot.config(fg=C["success"])
            self.lbl_conn_text.config(text="Conectado", fg=C["success"])
            self.btn_connect.config(state="disabled")
            self.btn_disconnect.config(state="normal")
            self.btn_enviar.config(state="normal")
            self.btn_multi.config(state="normal")
            self.ent_mensaje.focus()
        else:
            self.lbl_conn_dot.config(fg=C["error"])
            self.lbl_conn_text.config(text="Desconectado", fg=C["text_dim"])
            self.btn_connect.config(state="normal")
            self.btn_disconnect.config(state="disabled")
            self.btn_enviar.config(state="disabled")
            self.btn_multi.config(state="disabled")
            self.lbl_cola.config(text="Cola: —", fg=C["text_dim"])

    def _set_status(self, msg: str):
        self.lbl_status.config(text=msg)

    # ─────────────────────────────────────────────────────────
    # POLLING DEL SERVIDOR (estado de la cola)
    # ─────────────────────────────────────────────────────────

    def _poll_server(self):
        """Cada 2 segundos pregunta al servidor el estado de la cola."""
        if self.client:
            def _do():
                try:
                    data = self.client.cola()
                    self._log_queue.put(("COLA", data))
                except Exception:
                    pass
            threading.Thread(target=_do, daemon=True).start()
        self.after(2000, self._poll_server)


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    app = App()

    # Centrar ventana
    app.update_idletasks()
    w, h = 920, 700
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    app.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    app.mainloop()
