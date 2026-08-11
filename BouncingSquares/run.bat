@echo off
rem 双击运行：程序出错时保留窗口并显示 error.log，便于排查
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    python main.py
) else (
    py -3 main.py
)

if errorlevel 1 (
    echo.
    echo 程序异常退出，错误详情：
    if exist error.log type error.log
    echo.
    pause
)
