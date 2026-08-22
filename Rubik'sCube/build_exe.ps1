# 打包脚本：把 rubiks_cube_2d.py 编译成单文件 .exe
# 用法：powershell -ExecutionPolicy Bypass -File build_exe.ps1

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

# 1) 生成图标
python make_icon.py

# 2) 自检
python rubiks_cube_2d.py --selftest

# 3) PyInstaller 打包（单文件、无控制台窗口）
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name "RubiksCube2D" `
    --icon "icon.ico" `
    "rubiks_cube_2d.py"

Write-Host ""
Write-Host "打包完成: dist\RubiksCube2D.exe"
