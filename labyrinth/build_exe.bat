@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.10+ 并加入 PATH
    exit /b 1
)

echo [1/3] 安装依赖...
python -m pip install -r requirements.txt || exit /b 1

echo [2/3] 运行单元测试...
python -m unittest discover -s tests -v || exit /b 1

echo [3/3] 打包 exe（PyInstaller onefile + windowed）...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MazeGenerator main.py || exit /b 1

echo [4/4] 复制 exe 到项目上一级目录...
copy /y "dist\MazeGenerator.exe" "..\MazeGenerator.exe" >nul || exit /b 1

echo.
echo 完成！可执行文件: ..\MazeGenerator.exe
pause
