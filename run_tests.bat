@echo off
cd /d "%~dp0"
if not exist venv ( echo Run start.bat once first to set things up. & pause & exit /b 1 )
call venv\Scripts\activate
python -m unittest discover -s tests -v
pause
