$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Clock `
    --icon "$PSScriptRoot\clock.ico" `
    --add-data "$PSScriptRoot\clock.ico;." `
    clock.py `
    --distpath "$PSScriptRoot\.." `
    --workpath build `
    --specpath build

Write-Host "Done: $PSScriptRoot\..\Clock.exe"
