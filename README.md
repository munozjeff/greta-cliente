# Greta Cliente

> Cliente de escritorio para el sistema Greta Server — Consultas automatizadas de titularidad.

---

## 🚀 Instalación rápida

### Requisitos
- Python 3.10 o superior
- Google Chrome instalado

### Pasos

```bash
# 1. Clona el repositorio
git clone https://github.com/munozjeff/greta-cliente.git
cd greta-cliente

# 2. Crea un entorno virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. Ejecuta el cliente
python cliente_gui_titularidad.py
```

O simplemente haz doble clic en **`iniciar_cliente.bat`**

---

## 🔄 Actualizaciones automáticas

El cliente **detecta automáticamente** si hay una nueva versión disponible al iniciar.

Cuando hay una actualización:
1. Se muestra una ventana emergente con los cambios incluidos
2. Haz clic en **"Actualizar ahora"**
3. El cliente se descarga y reinicia automáticamente ✅

> La versión actual se guarda en `version.txt`

---

## 📋 Uso

1. Ingresa la **URL del servidor** (local o ngrok)
2. Ingresa la **API Key** del servidor
3. Haz clic en **Conectar**
4. Selecciona el tipo de búsqueda:
   - 📱 **Número de Teléfono**
   - 🪪 **Documento de Identidad** (CC, CE, PS, NIT, PPT)
5. Escribe el número y presiona **Consultar ▶** o `Enter`

---

## 📁 Archivos

| Archivo | Descripción |
|---|---|
| `cliente_gui_titularidad.py` | Aplicación principal |
| `updater.py` | Sistema de actualizaciones automáticas |
| `version.txt` | Versión actual instalada |
| `requirements.txt` | Dependencias de Python |
| `iniciar_cliente.bat` | Lanzador para Windows |

---

## 🛠 Para el desarrollador — Publicar una nueva versión

1. Actualiza `version.txt` con la nueva versión (ej: `1.1.0`)
2. Haz commit y push:
   ```bash
   git add .
   git commit -m "v1.1.0 — descripción de cambios"
   git push
   ```
3. En GitHub → **Releases → Create a new release**
   - Tag: `v1.1.0`
   - Título: `v1.1.0 — Nueva funcionalidad X`
   - Descripción: los cambios incluidos
   - **Adjuntar** `cliente_gui_titularidad.py` como asset del release
4. Publica el release → los clientes lo verán automáticamente al iniciar ✅

---

## 📜 Changelog

### v1.0.0
- Consulta de titularidad por teléfono y documento
- Sistema de actualizaciones automáticas desde GitHub
- Keep-alive de sesión integrado en el servidor
