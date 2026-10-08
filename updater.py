#!/usr/bin/env python3
"""
updater.py — Sistema de actualizaciones automaticas para Greta Cliente
=======================================================================
Verifica si hay una nueva version disponible en GitHub y ofrece
actualizar el cliente de forma automatica con un solo clic.

Repositorio: https://github.com/munozjeff/greta-cliente
"""

import os
import sys
import shutil
import logging
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
import requests

log = logging.getLogger("greta_updater")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACION
# ─────────────────────────────────────────────────────────────────────────────

REPO            = "munozjeff/greta-cliente"
GITHUB_API_URL  = f"https://api.github.com/repos/{REPO}/releases/latest"
ARCHIVO_CLIENTE = "cliente_gui_titularidad.py"
VERSION_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.txt")


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES DE VERSION
# ─────────────────────────────────────────────────────────────────────────────

def _parse_version(v: str) -> tuple:
    """Convierte '1.2.3' en (1, 2, 3) para comparacion."""
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except Exception:
        return (0, 0, 0)


def get_version_local() -> str:
    """Lee la version actual desde version.txt."""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "1.0.0"


def set_version_local(version: str):
    """Guarda la nueva version en version.txt."""
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(version.strip().lstrip("v"))


# ─────────────────────────────────────────────────────────────────────────────
# CONSULTA A GITHUB
# ─────────────────────────────────────────────────────────────────────────────

def get_latest_release() -> dict | None:
    """
    Consulta la API de GitHub para obtener el ultimo release.
    Retorna el JSON de la respuesta o None si falla.
    """
    try:
        r = requests.get(GITHUB_API_URL, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.debug("No se pudo consultar GitHub: %s", exc)
        return None


def hay_nueva_version() -> tuple[bool, str, dict | None]:
    """
    Verifica si hay una version mas nueva en GitHub.

    Returns:
        (hay_update, version_remota, release_data)
    """
    release = get_latest_release()
    if not release:
        return False, "", None

    version_remota = release.get("tag_name", "").lstrip("v")
    version_local  = get_version_local()

    if not version_remota:
        return False, "", None

    hay_update = _parse_version(version_remota) > _parse_version(version_local)
    return hay_update, version_remota, release


# ─────────────────────────────────────────────────────────────────────────────
# DESCARGA Y APLICACION DE ACTUALIZACION
# ─────────────────────────────────────────────────────────────────────────────

def _url_descarga(release: dict) -> str | None:
    """Busca la URL del archivo cliente en los assets del release."""
    # Primero buscar en los assets subidos al release
    for asset in release.get("assets", []):
        if asset["name"] == ARCHIVO_CLIENTE:
            return asset["browser_download_url"]

    # Fallback: descargar directamente del tag en el repo
    tag = release.get("tag_name", "main")
    return (
        f"https://raw.githubusercontent.com/{REPO}/{tag}/{ARCHIVO_CLIENTE}"
    )


def aplicar_actualizacion(release: dict, on_progreso=None) -> bool:
    """
    Descarga y reemplaza el archivo cliente con la nueva version.

    Args:
        release: datos del release de GitHub
        on_progreso: callback(str) para reportar progreso

    Returns:
        True si se actualizo exitosamente
    """
    def _prog(msg):
        log.info(msg)
        if on_progreso:
            on_progreso(msg)

    url = _url_descarga(release)
    if not url:
        _prog("No se encontro la URL de descarga.")
        return False

    _prog(f"Descargando desde: {url}")

    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        nuevo_contenido = r.text
    except Exception as exc:
        _prog(f"Error al descargar: {exc}")
        return False

    # Rutas de archivos
    carpeta   = os.path.dirname(os.path.abspath(__file__))
    ruta_orig = os.path.join(carpeta, ARCHIVO_CLIENTE)
    ruta_bak  = ruta_orig + ".bak"

    # Hacer backup del archivo actual
    if os.path.exists(ruta_orig):
        shutil.copy2(ruta_orig, ruta_bak)
        _prog("Backup creado: cliente_gui_titularidad.py.bak")

    # Escribir nueva version
    try:
        with open(ruta_orig, "w", encoding="utf-8") as f:
            f.write(nuevo_contenido)
        _prog("Archivo actualizado correctamente.")
    except Exception as exc:
        # Restaurar backup si falla
        if os.path.exists(ruta_bak):
            shutil.copy2(ruta_bak, ruta_orig)
        _prog(f"Error al escribir archivo: {exc}")
        return False

    # Actualizar version local
    nueva_ver = release.get("tag_name", "").lstrip("v")
    set_version_local(nueva_ver)
    _prog(f"Version actualizada a: {nueva_ver}")

    return True


def reiniciar_cliente():
    """Reinicia el proceso del cliente con la nueva version."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), ARCHIVO_CLIENTE)
    subprocess.Popen([sys.executable, script])
    sys.exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# DIALOGO DE ACTUALIZACION (Tkinter)
# ─────────────────────────────────────────────────────────────────────────────

class DialogoActualizacion(tk.Toplevel):
    """
    Ventana de dialogo que muestra la disponibilidad de una nueva version
    y permite actualizar con un solo clic.
    """

    C = {
        "bg":      "#0b0e17",
        "card":    "#131724",
        "accent":  "#4f8ef7",
        "success": "#22c55e",
        "error":   "#ef4444",
        "warning": "#f59e0b",
        "text":    "#e2e8f0",
        "dim":     "#475569",
    }

    def __init__(self, parent, version_local: str, version_remota: str, release: dict):
        super().__init__(parent)
        self.parent         = parent
        self.release        = release
        self.version_local  = version_local
        self.version_remota = version_remota
        self._actualizado   = False

        self.title("Actualización disponible")
        self.geometry("480x320")
        self.resizable(False, False)
        self.configure(bg=self.C["bg"])
        self.grab_set()
        self.lift()

        # Centrar ventana
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - 480) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 320) // 2
        self.geometry(f"480x320+{x}+{y}")

        self._build()

    def _build(self):
        # ── Encabezado ─────────────────────────────────────────────
        tk.Frame(self, bg=self.C["accent"], height=4).pack(fill="x")

        hdr = tk.Frame(self, bg=self.C["card"], pady=18, padx=24)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="🚀  Nueva versión disponible",
            font=("Segoe UI Bold", 14), bg=self.C["card"], fg=self.C["accent"]
        ).pack(anchor="w")

        tk.Label(
            hdr,
            text=f"  v{self.version_local}  →  v{self.version_remota}",
            font=("Segoe UI", 11), bg=self.C["card"], fg=self.C["text"]
        ).pack(anchor="w", pady=(4, 0))

        # ── Notas del release ──────────────────────────────────────
        notas_frame = tk.Frame(self, bg=self.C["bg"], padx=24, pady=10)
        notas_frame.pack(fill="both", expand=True)

        body = self.release.get("body", "Sin notas de versión.") or "Sin notas de versión."
        # Truncar si es muy largo
        if len(body) > 200:
            body = body[:200] + "..."

        tk.Label(
            notas_frame, text="Novedades:",
            font=("Segoe UI Semibold", 9), bg=self.C["bg"], fg=self.C["dim"]
        ).pack(anchor="w")

        tk.Label(
            notas_frame, text=body,
            font=("Segoe UI", 9), bg=self.C["bg"], fg=self.C["text"],
            wraplength=430, justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # ── Barra de progreso / estado ─────────────────────────────
        self.lbl_estado = tk.Label(
            self, text="",
            font=("Consolas", 9), bg=self.C["bg"], fg=self.C["dim"]
        )
        self.lbl_estado.pack(pady=(0, 4))

        # ── Botones ────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=self.C["bg"], pady=10, padx=24)
        btn_frame.pack(fill="x")

        self.btn_actualizar = tk.Button(
            btn_frame, text="  ⬇  Actualizar ahora  ",
            font=("Segoe UI Semibold", 10),
            bg=self.C["success"], fg="#0b1a10",
            relief="flat", bd=0, cursor="hand2",
            padx=14, pady=7,
            command=self._iniciar_actualizacion
        )
        self.btn_actualizar.pack(side="left", padx=(0, 10))

        tk.Button(
            btn_frame, text="Más tarde",
            font=("Segoe UI", 10),
            bg=self.C["card"], fg=self.C["dim"],
            relief="flat", bd=0, cursor="hand2",
            padx=12, pady=7,
            command=self.destroy
        ).pack(side="left")

    def _iniciar_actualizacion(self):
        """Ejecuta la actualizacion en un hilo y muestra el progreso."""
        self.btn_actualizar.config(
            state="disabled", text="  ⏳  Actualizando...",
            bg=self.C["card"], fg=self.C["dim"]
        )

        def _do():
            exito = aplicar_actualizacion(
                self.release,
                on_progreso=lambda m: self.after(0, lambda: self.lbl_estado.config(text=m))
            )
            self.after(0, lambda: self._finalizar(exito))

        threading.Thread(target=_do, daemon=True).start()

    def _finalizar(self, exito: bool):
        if exito:
            self.lbl_estado.config(
                text="✅ Actualización completada. Reiniciando...",
                fg=self.C["success"]
            )
            self.after(1500, reiniciar_cliente)
        else:
            self.lbl_estado.config(
                text="❌ Error al actualizar. Intenta manualmente.",
                fg=self.C["error"]
            )
            self.btn_actualizar.config(
                state="normal", text="  ⬇  Reintentar  ",
                bg=self.C["success"], fg="#0b1a10"
            )


# ─────────────────────────────────────────────────────────────────────────────
# FUNCION PUBLICA: verificar y mostrar dialogo si hay update
# ─────────────────────────────────────────────────────────────────────────────

def verificar_actualizacion_async(ventana_padre):
    """
    Verifica actualizaciones en un hilo daemon para no bloquear la UI.
    Si hay una nueva version, muestra el dialogo de actualizacion.

    Llamar desde el __init__ de la app principal.
    """
    def _check():
        try:
            hay_update, version_remota, release = hay_nueva_version()
            if hay_update and release:
                version_local = get_version_local()
                log.info(
                    "Nueva version disponible: v%s (actual: v%s)",
                    version_remota, version_local
                )
                ventana_padre.after(
                    500,  # Esperar 500ms para que la ventana principal este lista
                    lambda: DialogoActualizacion(
                        ventana_padre, version_local, version_remota, release
                    )
                )
            else:
                log.info("El cliente esta actualizado (v%s).", get_version_local())
        except Exception as exc:
            log.debug("Error al verificar actualizaciones: %s", exc)

    t = threading.Thread(target=_check, daemon=True, name="greta-updater")
    t.start()
