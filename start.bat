@echo off
setlocal
cd /d "%~dp0"
title TutorMatch Indore

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.9 or newer was not found.
  echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH", then run start.bat again.
  pause & exit /b 1
)
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
  if errorlevel 1 ( echo Could not create the virtual environment. & pause & exit /b 1 )
)
call venv\Scripts\activate
python -m pip install -q -r requirements.txt
if errorlevel 1 ( echo Package install failed. Check your internet connection and try again. & pause & exit /b 1 )

echo.
echo Starting TutorMatch Indore at http://127.0.0.1:8000  (close this window to stop)
echo Admin login: see README.md. Tutor activation codes (first start only): tutor_activation_codes.csv
echo.
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
