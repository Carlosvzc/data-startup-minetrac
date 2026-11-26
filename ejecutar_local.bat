@echo off
title MineTrac - tablero local
cd /d "%~dp0"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo No se encontro Python. Instala Python 3.11 o superior desde python.org y marca "Add to PATH".
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo No se pudo crear el entorno de Python.
  pause
  exit /b 1
)
echo Instalando dependencias. La primera vez tarda unos minutos, no cierres esta ventana...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Fallo la instalacion de dependencias. Copia el mensaje de arriba y mandalo.
  pause
  exit /b 1
)
set MINETRAC_ALCANCE=camiones
echo Abriendo MineTrac en http://localhost:8501 ...
".venv\Scripts\python.exe" -m streamlit run services\tablero\app.py --server.port 8501 --server.headless false
echo.
echo El tablero se detuvo o fallo. Copia el mensaje de arriba si hay un error.
pause
