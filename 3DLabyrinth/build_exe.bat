@echo off
REM 一键打包 3D 迷宫为独立 exe（首次运行前先执行：python -m pip install pyinstaller）
cd /d "%~dp0"
python -m PyInstaller --noconfirm --onefile --windowed --name 3DLabyrinth main.py
if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请确认已安装 PyInstaller
    pause
    exit /b 1
)
echo.
echo [完成] 已生成 dist\3DLabyrinth.exe
pause
