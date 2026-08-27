# Build a single-file, windowed Windows executable with PyInstaller.
# Usage:  powershell -ExecutionPolicy Bypass -File .\build_exe.ps1

param(
    [string]$Name = "SlotMachine"
)

$ErrorActionPreference = "Stop"

python -m pip install -r requirements-dev.txt

Write-Host "Running feature tests before build..." -ForegroundColor Cyan
python tests\test_features.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "TESTS FAILED - build aborted" -ForegroundColor Red
    exit 1
}

python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name $Name `
    --collect-all customtkinter `
    --hidden-import darkdetect `
    --version-file version_info.txt `
    --icon assets\icon.ico `
    --add-data "assets\icon.ico;assets" `
    --add-data "assets\sounds;assets\sounds" `
    main.py

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Build complete: $PWD\dist\$Name.exe" -ForegroundColor Green
