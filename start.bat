@echo off
REM Simple script to start everything on Windows
REM Usage: start.bat

echo Stopping old servers...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq rasa*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq app.py*" 2>nul
timeout /t 2 /nobreak >nul

echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Fix for OpenBLAS crashes (usually not needed on Windows, but included for compatibility)
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set VECLIB_MAXIMUM_THREADS=1
set NUMEXPR_NUM_THREADS=1

echo Starting Rasa server...
start "Rasa Server" cmd /k "rasa run --enable-api --cors *"

echo Waiting for Rasa to start...
timeout /t 8 /nobreak >nul

echo Starting Flask server...
start "Flask Server" cmd /k "python app.py"

echo.
echo Done! Servers running:
echo    - Rasa: http://localhost:5005
echo    - Chatbot: http://localhost:5001
echo.
echo Close the server windows to stop them, or run stop.bat
pause
