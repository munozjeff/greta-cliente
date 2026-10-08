@echo off
:: ============================================================
:: cliente\iniciar_cliente.bat  — Greta Cliente v1.0
:: ============================================================

title Greta Cliente

:: LOG: guardar toda la salida en un archivo para diagnostico
set LOGFILE=%~dp0inicio.log
echo [%date% %time%] Iniciando... > "%LOGFILE%"

echo.
echo  ===================================================
echo   GRETA CLIENTE  v1.0
echo   Iniciando...
echo  ===================================================
echo.

:: Posicionarse en la carpeta del .bat
cd /d "%~dp0"
echo [LOG] Directorio: %CD% >> "%LOGFILE%"

:: ──────────────────────────────────────────────
:: PASO 1 - Detectar Python
:: ──────────────────────────────────────────────
echo [1/3] Verificando Python...
echo [LOG] Paso 1: buscando Python >> "%LOGFILE%"

set PYTHON_CMD=

:: Intento 1: "python"
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    echo [LOG] Python encontrado como: python >> "%LOGFILE%"
    goto :python_ok
)

:: Intento 2: "py" launcher
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    echo [LOG] Python encontrado como: py >> "%LOGFILE%"
    goto :python_ok
)

:: Intento 3: rutas comunes
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe
if exist "C:\Python313\python.exe" set PYTHON_CMD=C:\Python313\python.exe
if exist "C:\Python312\python.exe" set PYTHON_CMD=C:\Python312\python.exe
if exist "C:\Python311\python.exe" set PYTHON_CMD=C:\Python311\python.exe
if exist "C:\Python310\python.exe" set PYTHON_CMD=C:\Python310\python.exe
if exist "%ProgramFiles%\Python311\python.exe" set PYTHON_CMD=%ProgramFiles%\Python311\python.exe
if exist "%ProgramFiles%\Python312\python.exe" set PYTHON_CMD=%ProgramFiles%\Python312\python.exe

if not "%PYTHON_CMD%"=="" (
    echo [LOG] Python encontrado en ruta: %PYTHON_CMD% >> "%LOGFILE%"
    goto :python_ok
)

echo [LOG] ERROR: Python no encontrado >> "%LOGFILE%"
echo.
echo  [ERROR] Python no encontrado en este equipo.
echo.
echo  Solucion:
echo  1. Descarga Python desde https://www.python.org/downloads/
echo  2. Durante la instalacion marca:  [x] Add Python to PATH
echo  3. Cierra y vuelve a abrir este archivo.
echo.
echo  Si ya tienes Python, abre CMD y ejecuta: python --version
echo  Si funciona, cierra y vuelve a abrir este .bat.
echo.
pause
exit /b 1

:python_ok
echo         OK - Python detectado: %PYTHON_CMD%
echo [LOG] Python OK: %PYTHON_CMD% >> "%LOGFILE%"

:: ──────────────────────────────────────────────
:: PASO 2 - Entorno virtual
:: ──────────────────────────────────────────────
echo [2/3] Verificando entorno virtual...
echo [LOG] Paso 2: verificando .venv >> "%LOGFILE%"

if exist ".venv\Scripts\activate.bat" (
    echo         OK - Entorno virtual encontrado.
    echo [LOG] .venv encontrado >> "%LOGFILE%"
) else (
    echo         Creando entorno virtual por primera vez...
    echo         ^(Esto solo ocurre una vez, por favor espera...^)
    echo [LOG] Creando .venv... >> "%LOGFILE%"
    "%PYTHON_CMD%" -m venv .venv >> "%LOGFILE%" 2>&1
    if errorlevel 1 (
        echo.
        echo  [ERROR] No se pudo crear el entorno virtual.
        echo  Revisa el archivo inicio.log para detalles.
        echo.
        pause
        exit /b 1
    )
    echo         OK - Entorno virtual creado.
    echo [LOG] .venv creado OK >> "%LOGFILE%"
)

:: Activar
call .venv\Scripts\activate.bat
echo [LOG] .venv activado >> "%LOGFILE%"

:: ──────────────────────────────────────────────
:: PASO 3 - Dependencias
:: ──────────────────────────────────────────────
echo [3/3] Verificando dependencias...
echo [LOG] Paso 3: dependencias >> "%LOGFILE%"

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo         Instalando requests ^(solo la primera vez...^)
    echo [LOG] Instalando requests... >> "%LOGFILE%"
    pip install requests >> "%LOGFILE%" 2>&1
    echo         OK - requests instalado.
    echo [LOG] requests instalado >> "%LOGFILE%"
) else (
    echo         OK - Dependencias ya instaladas.
    echo [LOG] requests ya disponible >> "%LOGFILE%"
)

:: ──────────────────────────────────────────────
:: LANZAR GUI
:: ──────────────────────────────────────────────
echo.
echo  ===================================================
echo   Todo listo. Abriendo cliente GUI...
echo   Esta ventana permanece abierta mientras
echo   el cliente este en uso.
echo  ===================================================
echo.
echo [LOG] Lanzando cliente_gui.py >> "%LOGFILE%"

python cliente_gui.py >> "%LOGFILE%" 2>&1

echo [LOG] cliente_gui.py termino con codigo: %errorlevel% >> "%LOGFILE%"

if errorlevel 1 (
    echo.
    echo  [AVISO] El cliente se cerro con un error.
    echo  Revisa el archivo inicio.log en esta carpeta para detalles.
    echo.
    type "%LOGFILE%"
    echo.
    pause
) else (
    echo  Cliente cerrado correctamente.
    pause
)
