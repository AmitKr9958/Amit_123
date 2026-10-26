# Run from the repository root in PowerShell.
$ErrorActionPreference = "Stop"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10+ is required. Install from https://www.python.org/downloads/windows/ and select Add Python to PATH."
}
if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m playwright install chromium
if (-not (Test-Path "config.json")) { Copy-Item "config.example.json" "config.json" }
New-Item -ItemType Directory -Force -Path "data" | Out-Null
Write-Host "Installed. Next: .\run.ps1 login"
