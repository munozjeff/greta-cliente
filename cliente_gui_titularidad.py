#!/usr/bin/env python3
"""
cliente_gui.py — Cliente GUI para Greta Server
===============================================
Interfaz grafica que permite:
  • Conectarse al servidor (local o internet via ngrok)
  • Consultar titularidad por numero de telefono o documento
  • Ver la respuesta organizada del cliente
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

# Importar el modulo de actualizaciones automaticas
try:
    from updater import verificar_actualizacion_async, get_version_local
    _UPDATER_DISPONIBLE = True
except ImportError:
    _UPDATER_DISPONIBLE = False
    def get_version_local(): return "1.0.0"
    def verificar_actualizacion_async(_): pass

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACION POR DEFECTO
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_URL    = "http://localhost:8000"
DEFAULT_APIKEY = "greta-test-2024"
DEFAULT_NOMBRE = "Agente-1"

# ─────────────────────────────────────────────────────────────────────────────
# PALETA DE COLORES
# ─────────────────────────────────────────────────────────────────────────────

C = {
    "bg":          "#0b0e17",
    "bg_card":     "#131724",
    "bg_input":    "#1c2133",
    "bg_panel":    "#0d1020",
    "bg_result":   "#0f1a2e",
    "accent":      "#4f8ef7",
    "accent2":     "#34d399",
    "accent3":     "#f59e0b",
    "success":     "#22c55e",
    "warning":     "#f59e0b",
    "error":       "#ef4444",
    "text":        "#e2e8f0",
    "text_dim":    "#475569",
    "text_mid":    "#94a3b8",
    "border":      "#1e2d4a",
    "border2":     "#2d3f60",
    "tag_send":    "#4f8ef7",
    "tag_recv":    "#34d399",
    "tag_err":     "#ef4444",
    "tag_sys":     "#475569",
    "tag_field":   "#94a3b8",
    "tag_val":     "#e2e8f0",
    "tag_head":    "#f59e0b",
}

FONT_MONO  = ("Consolas", 10)
FONT_LABEL = ("Segoe UI", 10)
FONT_BOLD  = ("Segoe UI Semibold", 10)
FONT_BIG   = ("Segoe UI Semibold", 13)
FONT_TITLE = ("Segoe UI Bold", 15)
FONT_SMALL = ("Segoe UI", 9)

# Tipos de documento disponibles
TIPOS_DOC = [
    ("CC  — Cédula de Ciudadanía",  "CC"),
    ("CE  — Cédula de Extranjería", "CE"),
    ("PS  — Pasaporte",             "PS"),
    ("NIT",                         "NIT"),
    ("PPT — Permiso Permanencia",   "PPT"),
]


# ─────────────────────────────────────────────────────────────────────────────
# CLIENTE HTTP
# ─────────────────────────────────────────────────────────────────────────────

class GretaClient:
    """Comunicacion HTTP con el servidor Greta."""

    def __init__(self, url: str, api_key: str, cliente_id: str):
        self.url        = url.rstrip("/")
        self.api_key    = api_key
        self.cliente_id = cliente_id
        self.headers    = {
            "X-API-Key":    api_key,
            "Content-Type": "application/json",
        }
        self.timeout = 200

    def health(self) -> dict:
        r = requests.get(f"{self.url}/health", timeout=10)
        r.raise_for_status()
        return r.json()

    def cola(self) -> dict:
        r = requests.get(f"{self.url}/cola", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def consultar(self, parametros: dict) -> dict:
        """Envia una consulta al endpoint /consultar."""
        payload = {
            "mensaje":    parametros.get("numero", ""),
            "cliente_id": self.cliente_id,
            "parametros": parametros,
        }
        r = requests.post(
            f"{self.url}/consultar",
            headers=self.headers,
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE UI
# ─────────────────────────────────────────────────────────────────────────────

def _entry(parent, width=28, show=None, default=""):
    e = tk.Entry(
        parent, width=width, font=FONT_MONO,
        bg=C["bg_input"], fg=C["text"], insertbackground=C["accent"],
        relief="flat", bd=0, highlightthickness=1,
        highlightbackground=C["border"], highlightcolor=C["accent"],
        **({"show": show} if show else {})
    )
    if default:
        e.insert(0, default)
    return e


def _label(parent, text, fg=None, font=None, bg=None):
    return tk.Label(
        parent, text=text,
        bg=bg or C["bg_card"], fg=fg or C["text_mid"],
        font=font or FONT_LABEL
    )


def _btn(parent, text, cmd, bg=None, fg="white", **kw):
    return tk.Button(
        parent, text=text, command=cmd,
        bg=bg or C["accent"], fg=fg,
        font=FONT_BOLD, relief="flat", bd=0,
        cursor="hand2", activebackground=C["border2"],
        activeforeground=C["text"], **kw
    )


# ─────────────────────────────────────────────────────────────────────────────
# VENTANA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        _version = get_version_local()
        self.title(f"Greta Server — Consultas  v{_version}")
        self.geometry("980x760")
        self.minsize(860, 640)
        self.configure(bg=C["bg"])

        self.client: GretaClient | None = None
        self._log_queue   = queue_module.Queue()
        self._contador    = 0

        # Variables de la consulta
        self._var_tipo_busqueda = tk.StringVar(value="telefono")
        self._var_tipo_doc      = tk.StringVar(value="CC")

        self._build_ui()
        self._process_log_queue()
        self._poll_server()

        # Verificar actualizaciones en segundo plano (no bloquea la UI)
        verificar_actualizacion_async(self)

    # ─────────────────────────────────────────────────────────
    # CONSTRUCCION DE UI
    # ─────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_connection_panel()
        self._build_query_panel()
        self._build_main_area()
        self._build_status_bar()

    def _build_header(self):
        hdr = tk.Frame(self, bg="#080b12", pady=12)
        hdr.pack(fill="x")

        # Barra de color superior
        tk.Frame(self, bg=C["accent"], height=3).pack(fill="x")

        inner = tk.Frame(hdr, bg="#080b12")
        inner.pack(fill="x", padx=20)

        tk.Label(
            inner, text="⬡  GRETA SERVER", font=FONT_TITLE,
            bg="#080b12", fg=C["accent"]
        ).pack(side="left")

        tk.Label(
            inner, text="  ·  Sistema de Consultas Automatizadas",
            font=FONT_LABEL, bg="#080b12", fg=C["text_dim"]
        ).pack(side="left")

        # Indicador conexion
        self.lbl_conn_dot  = tk.Label(inner, text="●", font=("Segoe UI", 16), bg="#080b12", fg=C["error"])
        self.lbl_conn_dot.pack(side="right", padx=(4, 0))
        self.lbl_conn_text = tk.Label(inner, text="Desconectado", font=FONT_LABEL, bg="#080b12", fg=C["text_dim"])
        self.lbl_conn_text.pack(side="right", padx=4)

        # Indicador sesion navegador
        self.lbl_sesion_dot  = tk.Label(inner, text="●", font=("Segoe UI", 16), bg="#080b12", fg=C["text_dim"])
        self.lbl_sesion_dot.pack(side="right", padx=(16, 0))
        self.lbl_sesion_text = tk.Label(inner, text="Sesion: —", font=FONT_LABEL, bg="#080b12", fg=C["text_dim"])
        self.lbl_sesion_text.pack(side="right")

    def _build_connection_panel(self):
        pnl = tk.Frame(self, bg=C["bg_card"], pady=10, padx=16)
        pnl.pack(fill="x", padx=14, pady=(10, 4))

        row1 = tk.Frame(pnl, bg=C["bg_card"])
        row1.pack(fill="x", pady=(0, 8))

        _label(row1, "URL Servidor", font=FONT_BOLD).pack(side="left")
        self.ent_url = _entry(row1, width=38, default=DEFAULT_URL)
        self.ent_url.pack(side="left", padx=(8, 20), ipady=5, ipadx=4)

        _label(row1, "API Key", font=FONT_BOLD).pack(side="left")
        self.ent_apikey = _entry(row1, width=24, show="•", default=DEFAULT_APIKEY)
        self.ent_apikey.pack(side="left", padx=(8, 6), ipady=5, ipadx=4)

        tk.Button(
            row1, text="👁", font=("Segoe UI", 10),
            bg=C["bg_input"], fg=C["text_mid"],
            relief="flat", bd=0, cursor="hand2",
            command=lambda: self.ent_apikey.config(
                show="" if self.ent_apikey.cget("show") == "•" else "•"
            )
        ).pack(side="left")

        row2 = tk.Frame(pnl, bg=C["bg_card"])
        row2.pack(fill="x")

        _label(row2, "Mi nombre", font=FONT_BOLD).pack(side="left")
        self.ent_nombre = _entry(row2, width=18, default=DEFAULT_NOMBRE)
        self.ent_nombre.pack(side="left", padx=(8, 16), ipady=5, ipadx=4)

        self.btn_connect = _btn(row2, "  Conectar  ", self._conectar, padx=12, pady=4)
        self.btn_connect.pack(side="left", padx=(0, 8))

        self.btn_disconnect = _btn(
            row2, "Desconectar", self._desconectar,
            bg=C["bg_input"], fg=C["text_dim"], state="disabled", padx=10, pady=4
        )
        self.btn_disconnect.pack(side="left")

        self.lbl_cola = _label(row2, "Cola: —", fg=C["text_dim"], font=FONT_BOLD)
        self.lbl_cola.pack(side="right", padx=8)

    def _build_query_panel(self):
        """Panel de formulario de consulta."""
        outer = tk.Frame(self, bg=C["bg_card"], pady=14, padx=16)
        outer.pack(fill="x", padx=14, pady=(2, 4))

        # Título
        tk.Label(
            outer, text="📋  Nueva Consulta",
            font=FONT_BIG, bg=C["bg_card"], fg=C["text"]
        ).pack(anchor="w", pady=(0, 10))

        # ── Tipo de consulta (por ahora solo titularidad) ──
        tipo_frame = tk.Frame(outer, bg=C["bg_card"])
        tipo_frame.pack(fill="x", pady=(0, 10))

        _label(tipo_frame, "Tipo de consulta:", font=FONT_BOLD).pack(side="left")

        # Botón tipo consulta (pill activo)
        self.btn_titularidad = tk.Button(
            tipo_frame, text="✅  Validar Titularidad",
            font=FONT_BOLD, bg=C["accent"], fg="white",
            relief="flat", bd=0, padx=14, pady=5,
            state="disabled"  # Se habilita al conectar
        )
        self.btn_titularidad.pack(side="left", padx=(10, 0))

        # ── Tipo de búsqueda ──
        busq_frame = tk.Frame(outer, bg=C["bg_card"])
        busq_frame.pack(fill="x", pady=(0, 8))

        _label(busq_frame, "Buscar por:", font=FONT_BOLD).pack(side="left")

        rb_tel = tk.Radiobutton(
            busq_frame, text="📱  Número de Teléfono",
            variable=self._var_tipo_busqueda, value="telefono",
            bg=C["bg_card"], fg=C["text"], selectcolor=C["bg_input"],
            activebackground=C["bg_card"], activeforeground=C["accent2"],
            font=FONT_LABEL, command=self._on_tipo_busqueda_change
        )
        rb_tel.pack(side="left", padx=(12, 0))

        rb_doc = tk.Radiobutton(
            busq_frame, text="🪪  Documento de Identidad",
            variable=self._var_tipo_busqueda, value="documento",
            bg=C["bg_card"], fg=C["text"], selectcolor=C["bg_input"],
            activebackground=C["bg_card"], activeforeground=C["accent2"],
            font=FONT_LABEL, command=self._on_tipo_busqueda_change
        )
        rb_doc.pack(side="left", padx=(16, 0))

        # ── Fila de campos ──
        campos_frame = tk.Frame(outer, bg=C["bg_card"])
        campos_frame.pack(fill="x", pady=(0, 4))

        # Tipo de documento (visible solo cuando es búsqueda por documento)
        self.frm_tipo_doc = tk.Frame(campos_frame, bg=C["bg_card"])
        _label(self.frm_tipo_doc, "Tipo de doc:", font=FONT_BOLD).pack(side="left")

        self.cmb_tipo_doc = ttk.Combobox(
            self.frm_tipo_doc,
            textvariable=self._var_tipo_doc,
            values=[d[0] for d in TIPOS_DOC],
            state="readonly", width=30, font=FONT_LABEL
        )
        self.cmb_tipo_doc.current(0)
        self.cmb_tipo_doc.pack(side="left", padx=(8, 20), ipady=4)
        # Mapear la selección al código
        self.cmb_tipo_doc.bind("<<ComboboxSelected>>", self._on_doc_type_change)
        self._doc_key = "CC"  # valor actual

        # Número a consultar
        _label(campos_frame, "Número:", font=FONT_BOLD, bg=C["bg_card"]).pack(side="left")
        self.ent_numero = tk.Entry(
            campos_frame, width=24, font=("Segoe UI", 13),
            bg=C["bg_input"], fg=C["text"], insertbackground=C["accent"],
            relief="flat", bd=0, highlightthickness=2,
            highlightbackground=C["border"], highlightcolor=C["accent"]
        )
        self.ent_numero.pack(side="left", padx=(8, 12), ipady=7, ipadx=8)
        self.ent_numero.bind("<Return>", lambda e: self._enviar_consulta())

        self.btn_consultar = tk.Button(
            campos_frame, text="  Consultar  ▶",
            font=("Segoe UI Semibold", 11), bg=C["accent2"],
            fg="#0b1a10", relief="flat", bd=0, cursor="hand2",
            padx=16, pady=7, state="disabled",
            command=self._enviar_consulta
        )
        self.btn_consultar.pack(side="left")

        # Ocultar tipo doc por defecto (arranca en "telefono")
        self.frm_tipo_doc.pack_forget()

    def _build_main_area(self):
        """Area principal: resultado + log."""
        container = tk.Frame(self, bg=C["bg"])
        container.pack(fill="both", expand=True, padx=14, pady=4)
        container.columnconfigure(0, weight=3)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(0, weight=1)

        # ── Panel de resultado (izquierda) ──
        res_outer = tk.Frame(container, bg=C["bg_result"])
        res_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        tk.Label(
            res_outer, text="  Resultado de la Consulta",
            font=FONT_BOLD, bg="#0a1628", fg=C["accent"],
            anchor="w", pady=7
        ).pack(fill="x")

        # Contenido del resultado
        res_scroll = tk.Frame(res_outer, bg=C["bg_result"])
        res_scroll.pack(fill="both", expand=True, padx=10, pady=8)

        self.txt_resultado = scrolledtext.ScrolledText(
            res_scroll,
            font=FONT_MONO, bg=C["bg_result"], fg=C["text"],
            relief="flat", bd=0, padx=10, pady=8,
            state="disabled", wrap="word",
            insertbackground=C["accent"],
        )
        self.txt_resultado.pack(fill="both", expand=True)

        # Tags del resultado
        self.txt_resultado.tag_config("HEAD",  foreground=C["tag_head"],  font=("Consolas", 10, "bold"))
        self.txt_resultado.tag_config("FIELD", foreground=C["accent"],    font=("Consolas", 9))
        self.txt_resultado.tag_config("VALUE", foreground=C["text"])
        self.txt_resultado.tag_config("OK",    foreground=C["success"],   font=("Consolas", 10, "bold"))
        self.txt_resultado.tag_config("ERR",   foreground=C["error"],     font=("Consolas", 10, "bold"))
        self.txt_resultado.tag_config("DIM",   foreground=C["text_dim"])
        self.txt_resultado.tag_config("SEP",   foreground=C["border2"])

        # ── Log de actividad (derecha) ──
        log_outer = tk.Frame(container, bg=C["bg_panel"])
        log_outer.grid(row=0, column=1, sticky="nsew")

        tk.Label(
            log_outer, text="  Actividad",
            font=FONT_BOLD, bg="#080c14", fg=C["text_mid"],
            anchor="w", pady=7
        ).pack(fill="x")

        self.txt_log = scrolledtext.ScrolledText(
            log_outer,
            font=("Consolas", 9), bg=C["bg_panel"], fg=C["text"],
            relief="flat", bd=0, padx=10, pady=6,
            state="disabled", wrap="word",
        )
        self.txt_log.pack(fill="both", expand=True)

        self.txt_log.tag_config("SEND",  foreground=C["tag_send"])
        self.txt_log.tag_config("RECV",  foreground=C["tag_recv"])
        self.txt_log.tag_config("ERROR", foreground=C["tag_err"])
        self.txt_log.tag_config("SYS",   foreground=C["tag_sys"])
        self.txt_log.tag_config("TIME",  foreground=C["text_dim"])
        self.txt_log.tag_config("BOLD",  font=("Consolas", 9, "bold"))

        # Botón limpiar
        tk.Button(
            log_outer, text="Limpiar log", font=FONT_SMALL,
            bg=C["bg_panel"], fg=C["text_dim"],
            relief="flat", bd=0, cursor="hand2",
            command=self._limpiar_log
        ).pack(side="right", padx=8, pady=4)

    def _build_status_bar(self):
        bar = tk.Frame(self, bg="#05070d", pady=4)
        bar.pack(fill="x", side="bottom")
        self.lbl_status = tk.Label(
            bar, text="Ingresa la URL del servidor y haz clic en Conectar.",
            font=FONT_SMALL, bg="#05070d", fg=C["text_dim"], anchor="w"
        )
        self.lbl_status.pack(side="left", padx=16)

    # ─────────────────────────────────────────────────────────
    # EVENTOS DE FORMULARIO
    # ─────────────────────────────────────────────────────────

    def _on_tipo_busqueda_change(self):
        tipo = self._var_tipo_busqueda.get()
        if tipo == "documento":
            # Mostrar selector de tipo de documento
            self.frm_tipo_doc.pack(side="left", before=self.ent_numero.master)
        else:
            self.frm_tipo_doc.pack_forget()
        self.ent_numero.delete(0, "end")
        self.ent_numero.focus()

    def _on_doc_type_change(self, event=None):
        sel = self.cmb_tipo_doc.current()
        self._doc_key = TIPOS_DOC[sel][1]

    # ─────────────────────────────────────────────────────────
    # CONEXION
    # ─────────────────────────────────────────────────────────

    def _conectar(self):
        url    = self.ent_url.get().strip()
        apikey = self.ent_apikey.get().strip()
        nombre = self.ent_nombre.get().strip() or "Agente"

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

    # ─────────────────────────────────────────────────────────
    # ENVIO DE CONSULTA
    # ─────────────────────────────────────────────────────────

    def _enviar_consulta(self):
        if not self.client:
            return

        numero = self.ent_numero.get().strip()
        if not numero:
            self.ent_numero.focus()
            messagebox.showwarning("Campo vacío", "Ingresa el número a consultar.")
            return

        tipo_busqueda = self._var_tipo_busqueda.get()
        tipo_doc      = self._doc_key if tipo_busqueda == "documento" else None

        self._contador += 1
        nombre = self.ent_nombre.get().strip() or "Agente"

        parametros = {
            "tipo_consulta":  "validar_titularidad",
            "tipo_busqueda":  tipo_busqueda,
            "numero":         numero,
        }
        if tipo_doc:
            parametros["tipo_doc"] = tipo_doc

        # Bloquear UI mientras consulta
        self.btn_consultar.config(state="disabled", text="  Consultando...  ⏳")
        self.ent_numero.config(state="disabled")

        # Log de envio
        tipo_str = f"Teléfono: {numero}" if tipo_busqueda == "telefono" else f"Doc {tipo_doc}: {numero}"
        self._log_append(
            f"[{self._ts()}] ", "TIME",
            f"▶ Titularidad  ", "SEND",
            f"→ {tipo_str}\n", "BOLD"
        )
        self._mostrar_resultado_placeholder(f"Consultando {tipo_str}...")

        def _do():
            t0 = time.time()
            try:
                c = GretaClient(self.client.url, self.client.api_key, nombre)
                resultado = c.consultar(parametros)
                elapsed = round(time.time() - t0, 2)
                self._log_queue.put(("RECV_TITULARIDAD", nombre, resultado, elapsed))
            except requests.exceptions.Timeout:
                self._log_queue.put(("ERROR_Q", "Timeout: el servidor no respondio."))
            except requests.exceptions.ConnectionError:
                self._log_queue.put(("ERROR_Q", "Error de conexion. El servidor esta activo?"))
            except requests.exceptions.HTTPError as e:
                try:
                    detail = e.response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                self._log_queue.put(("ERROR_Q", f"HTTP {e.response.status_code}: {detail}"))
            except Exception as e:
                self._log_queue.put(("ERROR_Q", str(e)))

        threading.Thread(target=_do, daemon=True).start()

    # ─────────────────────────────────────────────────────────
    # MOSTRAR RESULTADO
    # ─────────────────────────────────────────────────────────

    def _mostrar_resultado_placeholder(self, msg: str):
        self.txt_resultado.config(state="normal")
        self.txt_resultado.delete("1.0", "end")
        self.txt_resultado.insert("end", f"\n  ⏳ {msg}\n", "DIM")
        self.txt_resultado.config(state="disabled")

    def _mostrar_resultado_titularidad(self, resultado: dict, elapsed: float):
        """Formatea y muestra la informacion del cliente en el panel de resultado."""
        self.txt_resultado.config(state="normal")
        self.txt_resultado.delete("1.0", "end")

        r      = resultado.get("resultado", {})
        cliente = r.get("cliente", {})
        encontrado = r.get("encontrado", False)

        ts = self._ts()

        if not encontrado:
            self.txt_resultado.insert("end", "\n  ✗  CLIENTE NO ENCONTRADO\n", "ERR")
            self.txt_resultado.insert("end", f"\n  Número consultado: {r.get('valor_buscado','—')}\n", "DIM")
            self.txt_resultado.config(state="disabled")
            return

        # ── Cabecera ──────────────────────────────────────────────────────
        busqueda_label = (
            f"Teléfono: {r.get('valor_buscado','')}"
            if r.get("tipo_busqueda") == "telefono"
            else f"Doc {r.get('tipo_documento','')}: {r.get('valor_buscado','')}"
        )

        self.txt_resultado.insert("end", "\n")
        self.txt_resultado.insert("end", "  ✅  TITULARIDAD ENCONTRADA\n", "OK")
        self.txt_resultado.insert("end", f"  {busqueda_label}  ·  {ts}  ·  {elapsed}s\n", "DIM")
        self.txt_resultado.insert("end", "  " + "─" * 52 + "\n", "SEP")

        # ── Secciones de datos ────────────────────────────────────────────
        secciones = [
            ("  👤  IDENTIFICACIÓN", [
                ("Tipo",    cliente.get("tipo_identificacion")),
                ("Número",  cliente.get("numero_identificacion")),
            ]),
            ("  📛  NOMBRES", [
                ("Primer nombre",    cliente.get("primer_nombre")),
                ("Segundo nombre",   cliente.get("segundo_nombre")),
                ("Apellido",         cliente.get("apellido")),
                ("Segundo apellido", cliente.get("segundo_apellido")),
            ]),
            ("  🗂  DATOS PERSONALES", [
                ("Fecha nacimiento", cliente.get("fecha_nacimiento")),
                ("Género",          cliente.get("genero")),
                ("Título",          cliente.get("titulo")),
                ("Ocupación",       cliente.get("ocupacion")),
                ("Grupo étnico",    cliente.get("grupo_etnico")),
            ]),
            ("  🏆  NIVEL DE CLIENTE", [
                ("Estado",       cliente.get("estado_cliente")),
                ("Nivel",        cliente.get("nivel_cliente")),
                ("Segmento",     cliente.get("segmento")),
                ("Subsegmento",  cliente.get("subsegmento")),
                ("Estrato",      cliente.get("estrato")),
            ]),
            ("  📞  CONTACTO", [
                ("Email",       cliente.get("email")),
                ("Celular",     cliente.get("contacto_celular")),
                ("Contacto 2",  cliente.get("contacto_2")),
                ("Contacto 3",  cliente.get("contacto_3")),
            ]),
            ("  📝  ADMINISTRATIVO", [
                ("Fecha creación",  cliente.get("fecha_creacion")),
                ("Observaciones",  cliente.get("observaciones")),
                ("Visibilidad",    cliente.get("visibilidad_info")),
            ]),
        ]

        for titulo, campos in secciones:
            # Filtrar campos vacíos
            campos_val = [(k, v) for k, v in campos if v]
            if not campos_val:
                continue
            self.txt_resultado.insert("end", f"\n{titulo}\n", "HEAD")
            for campo, valor in campos_val:
                self.txt_resultado.insert("end", f"    {campo:<22}", "FIELD")
                self.txt_resultado.insert("end", f"{valor}\n", "VALUE")

        self.txt_resultado.insert("end", "\n  " + "─" * 52 + "\n", "SEP")
        self.txt_resultado.insert(
            "end",
            f"  Job ID: {resultado.get('job_id','')[:8]}  ·  "
            f"Tiempo total: {elapsed}s\n",
            "DIM"
        )

        self.txt_resultado.see("1.0")
        self.txt_resultado.config(state="disabled")

    # ─────────────────────────────────────────────────────────
    # LOG (thread-safe)
    # ─────────────────────────────────────────────────────────

    def _process_log_queue(self):
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
            sesion = data.get("navegador", {})
            self._log_sys(
                f"Conectado | Cola: {data.get('cola', '?')} | "
                f"Sesion: {'✅ Activa' if sesion.get('sesion_activa') else '⏳ Esperando login'}"
            )
            self._set_status(f"Conectado a {self.client.url}")
            self._actualizar_indicador_sesion(sesion)

        elif kind == "SYS_ERR":
            self._log_err(f"No se pudo conectar: {item[1]}")
            self._set_status("Error de conexion")
            self.client = None

        elif kind == "RECV_TITULARIDAD":
            _, nombre, resultado, elapsed = item
            encontrado = resultado.get("resultado", {}).get("encontrado", False)
            self._mostrar_resultado_titularidad(resultado, elapsed)
            if encontrado:
                self._log_append(
                    f"[{self._ts()}] ", "TIME",
                    f"◀ Titularidad  ", "RECV",
                    f"← Encontrado en {elapsed}s\n", "BOLD"
                )
            else:
                self._log_append(
                    f"[{self._ts()}] ", "TIME",
                    f"◀ Titularidad  ", "RECV",
                    f"← No encontrado ({elapsed}s)\n", "TIME"
                )
            # Rehabilitar UI
            self.btn_consultar.config(state="normal", text="  Consultar  ▶")
            self.ent_numero.config(state="normal")
            self.ent_numero.focus()

        elif kind == "ERROR_Q":
            error = item[1]
            self._log_err(f"Error: {error}")
            self.txt_resultado.config(state="normal")
            self.txt_resultado.delete("1.0", "end")
            self.txt_resultado.insert("end", f"\n  ✗  ERROR\n\n  {error}\n", "ERR")
            self.txt_resultado.config(state="disabled")
            self.btn_consultar.config(state="normal", text="  Consultar  ▶")
            self.ent_numero.config(state="normal")

        elif kind == "COLA":
            cola_data = item[1]
            pend    = cola_data.get("pendientes_en_cola", 0)
            activos = cola_data.get("jobs_activos_total", 0)
            self.lbl_cola.config(
                text=f"Cola: {pend} pend | {activos} activos",
                fg=C["warning"] if pend > 0 else C["text_mid"]
            )

        elif kind == "SESION":
            sesion = item[1]
            self._actualizar_indicador_sesion(sesion)

    def _actualizar_indicador_sesion(self, sesion: dict):
        if sesion.get("sesion_activa"):
            self.lbl_sesion_dot.config(fg=C["success"])
            self.lbl_sesion_text.config(text="Sesion: Activa", fg=C["success"])
        elif sesion.get("inicializando") or sesion.get("driver_activo"):
            self.lbl_sesion_dot.config(fg=C["warning"])
            self.lbl_sesion_text.config(text="Sesion: Esperando login", fg=C["warning"])
        else:
            self.lbl_sesion_dot.config(fg=C["text_dim"])
            self.lbl_sesion_text.config(text="Sesion: —", fg=C["text_dim"])

    def _log_append(self, *parts):
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
            self.btn_consultar.config(state="normal")
            self.btn_titularidad.config(state="normal")
            self.ent_numero.focus()
        else:
            self.lbl_conn_dot.config(fg=C["error"])
            self.lbl_conn_text.config(text="Desconectado", fg=C["text_dim"])
            self.btn_connect.config(state="normal")
            self.btn_disconnect.config(state="disabled")
            self.btn_consultar.config(state="disabled")
            self.btn_titularidad.config(state="disabled")
            self.lbl_cola.config(text="Cola: —", fg=C["text_dim"])

    def _set_status(self, msg: str):
        self.lbl_status.config(text=msg)

    # ─────────────────────────────────────────────────────────
    # POLLING
    # ─────────────────────────────────────────────────────────

    def _poll_server(self):
        """Cada 3s consulta el estado del servidor (cola + sesion)."""
        if self.client:
            def _do():
                try:
                    data = self.client.health()
                    self._log_queue.put(("COLA", data))
                    sesion = data.get("navegador", {})
                    self._log_queue.put(("SESION", sesion))
                except Exception:
                    pass
            threading.Thread(target=_do, daemon=True).start()
        self.after(3000, self._poll_server)


if __name__ == "__main__":
    app = App()
    app.update_idletasks()
    w, h = 980, 760
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    app.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    app.mainloop()
