@echo off
REM Script to stop Rasa, train, and run on Windows
REM Usage: train_and_run.bat

cd /d "%~dp0"

echo Stopping Rasa server...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq rasa*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq app.py*" 2>nul
timeout /t 2 /nobreak >nul

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Training Rasa model...
rasa train

if %ERRORLEVEL% EQU 0 (
    echo Training completed successfully!
    echo Starting servers...
    call start.bat
) else (
    echo Training failed. Please check the errors above.
    pause
    exit /b 1
)




