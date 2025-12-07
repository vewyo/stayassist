@echo off
REM Simple script to stop everything on Windows
REM Usage: stop.bat

echo Stopping servers...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq rasa*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq app.py*" 2>nul
timeout /t 1 /nobreak >nul
echo Servers stopped
