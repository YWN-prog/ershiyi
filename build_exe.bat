@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt pyinstaller
py -3 -m PyInstaller --noconfirm --clean --onedir --name 声音克隆工具 --collect-all gradio --collect-all safehttpx --collect-all groovy --collect-all qwen_tts --copy-metadata torchcodec --copy-metadata transformers app.py
copy /Y config.json "dist\声音克隆工具\config.json" >nul
copy /Y engine_adapter.py "dist\声音克隆工具\engine_adapter.py" >nul
copy /Y requirements-model.txt "dist\声音克隆工具\requirements-model.txt" >nul
copy /Y 安装模型.bat "dist\声音克隆工具\安装模型.bat" >nul
echo 打包完成：dist\声音克隆工具\声音克隆工具.exe
pause
