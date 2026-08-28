# 一键构建 dist/Radar.exe（需要先安装 PyInstaller: pip install -r requirements.txt）
$ErrorActionPreference = "Stop"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Radar main.py
Write-Host ""
Write-Host "构建完成: $PSScriptRoot\dist\Radar.exe"
