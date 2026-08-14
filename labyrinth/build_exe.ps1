# 一键构建 MazeGenerator.exe
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "[1/3] 安装依赖..."
python -m pip install -r requirements.txt

Write-Host "[2/3] 运行单元测试..."
python -m unittest discover -s tests -v

Write-Host "[3/3] 打包 exe（PyInstaller onefile + windowed）..."
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MazeGenerator main.py

Write-Host "[4/4] 复制 exe 到项目上一级目录..."
Copy-Item -LiteralPath "dist\MazeGenerator.exe" -Destination "..\MazeGenerator.exe" -Force

Write-Host ""
Write-Host "完成！可执行文件: ..\MazeGenerator.exe"
