# Run from the repository root.
$ErrorActionPreference = "Stop"
if (-not (Test-Path ".\.venv\Scripts\python.exe")) { throw "Not installed yet. Run .\install.ps1" }
& ".\.venv\Scripts\python.exe" run.py @args
