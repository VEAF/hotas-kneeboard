# Builds dist/HOTAS-Kneeboard.exe: the UI, then the executable.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
Push-Location web
npm ci
npm run build
Pop-Location
uv sync --frozen
uv run pyinstaller --noconfirm --clean packaging/hotas-kneeboard.spec
Get-Item dist/HOTAS-Kneeboard.exe
