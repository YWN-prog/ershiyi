@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found. Install Python 3.11 or 3.12 first.
  pause
  exit /b 1
)

echo Installing F5-TTS model dependencies...
py -3 -m pip install -r "%~dp0requirements-model.txt"
if errorlevel 1 (
  echo Installation failed. Read the error above and try again.
  pause
  exit /b 1
)

echo Dependencies installed. Model weights download on first generation.
pause
