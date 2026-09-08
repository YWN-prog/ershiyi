@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 was not found. Install Python 3.11 or 3.12 first.
  pause
  exit /b 1
)

py -3 -c "import gradio" >nul 2>nul
if errorlevel 1 (
  echo Installing interface dependencies...
  py -3 -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo Interface dependency installation failed.
    pause
    exit /b 1
  )
)

where f5-tts_infer-cli >nul 2>nul
if errorlevel 1 (
  echo F5-TTS is not installed.
  choice /M "Install model dependencies now"
  if errorlevel 1 py -3 -m pip install -r "%~dp0requirements-model.txt"
)

py -3 app.py
pause
