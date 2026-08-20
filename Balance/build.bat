@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/2] 安装依赖...
python -m pip install -r requirements.txt || goto :fail

echo [2/2] 打包 exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DeepSeekBalance --icon assets\icon.ico --add-data "assets\icon.ico;assets" main.py || goto :fail

echo.
echo 构建完成：dist\DeepSeekBalance.exe
pause
exit /b 0

:fail
echo.
echo 构建失败，请检查上方错误信息。
pause
exit /b 1
