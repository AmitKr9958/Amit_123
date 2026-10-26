@echo off
REM Daily supervised Naukri run (Windows)
REM Schedule via setup_task.ps1 or Task Scheduler GUI.
REM The browser window will open — complete any OTP if asked.

setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\activate.bat" (
  echo Virtualenv not found. Run: python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
  exit /b 1
)

call .venv\Scripts\activate.bat

REM Dry-run by default (search + score only). Change to "run --apply" after you trust the flow.
set CMD=python -m src.cli run
REM set CMD=python -m src.cli run --apply

echo [%date% %time%] Starting: %CMD%
%CMD%
set ERR=%ERRORLEVEL%
echo [%date% %time%] Finished with code %ERR%
exit /b %ERR%
