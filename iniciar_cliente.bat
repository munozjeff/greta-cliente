@echo off
title Greta Cliente - Validar Titularidad
cd /d "%~dp0"

set LOGFILE=%~dp0error_cliente.log
echo [%date% %time%] Iniciando cliente... > "%LOGFILE%"

echo ===================================================
echo   GRETA CLIENTE v2.0 — Validar Titularidad
echo ===================================================
echo.

set PYCMD=python
python --version >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    py --version >> "%LOGFILE%" 2>&1
    if not errorlevel 1 set PYCMD=py
)

echo Usando ejecutable: %PYCMD%
echo [LOG] Ejecutable: %PYCMD% >> "%LOGFILE%"

if exist ".venv\Scripts\activate.bat" (
    echo Activando entorno virtual .venv...
    call .venv\Scripts\activate.bat >> "%LOGFILE%" 2>&1
)

echo Instalando/Verificando requests...
%PYCMD% -m pip install requests >> "%LOGFILE%" 2>&1

echo.
echo Ejecutando cliente_gui_titularidad.py ...
echo.

%PYCMD% cliente_gui_titularidad.py >> "%LOGFILE%" 2>&1

if errorlevel 1 (
    echo.
    echo ===================================================
    echo   [ERROR] EL CLIENTE NO PUDO INICIAR
    echo ===================================================
    echo.
    echo A continuacion se muestra el error exacto:
    echo ---------------------------------------------------
    type "%LOGFILE%"
    echo ---------------------------------------------------
    echo.
)

pause
