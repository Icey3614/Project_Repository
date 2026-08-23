@echo off
cd /d "%~dp0"
python tools\make_icon.py
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Snake --icon assets\icon.ico --add-data "assets\icon.png;assets" main.py
echo.
echo 打包完成：dist\Snake.exe
pause
