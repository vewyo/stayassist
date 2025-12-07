# StayAssist Chatbot

An intelligent chatbot for hotel bookings built with Rasa Pro and Flask.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment (`.venv`)
- Git Bash (Windows) or Terminal (Mac/Linux)

### Simple Commands

**Mac/Linux:**
```bash
# Stop everything (if servers are running)
./stop.sh

# Start everything
./start.sh

# Train and then start
./train_and_run.sh
```

**Windows (using Git Bash):**
```bash
# Stop everything (if servers are running)
./stop.sh

# Start everything
./start.sh

# Train and then start
./train_and_run.sh
```

**Windows (using Command Prompt/PowerShell - EASIEST):**
```cmd
REM Stop everything (if servers are running)
stop.bat

REM Start everything
start.bat

REM Train and then start
train_and_run.bat
```

**Windows (Manual - Command Prompt/PowerShell):**
```cmd
REM Stop everything
taskkill /F /IM python.exe /FI "WINDOWTITLE eq rasa*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq app.py*" 2>nul

REM Activate virtual environment
.venv\Scripts\activate

REM Set environment variables (for OpenBLAS crash fix)
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set VECLIB_MAXIMUM_THREADS=1
set NUMEXPR_NUM_THREADS=1

REM Start Rasa (in one terminal)
start "Rasa Server" cmd /k "rasa run --enable-api --cors *"

REM Wait a few seconds
timeout /t 8 /nobreak

REM Start Flask (in another terminal)
start "Flask Server" cmd /k "python app.py"
```

## 🎤 Natural Voice (ElevenLabs) - Optional

The chatbot uses **ElevenLabs** for ultra-natural, human-like voice synthesis. If you want to use this feature:

1. **Get an ElevenLabs API Key:**
   - Sign up at [elevenlabs.io](https://elevenlabs.io)
   - Go to your dashboard → **Profile** → **API Keys**
   - Click **"Add API Key"** or **"Create New Key"**
   - **Required Permission:** ✅ **"Text to Speech"** (must be enabled)
   - **Optional Permission:** ✅ **"Voices (Read only)"** (recommended, to see available voices)
   - Copy your API key (starts with `sk-...`)
   - Free tier includes 10,000 characters/month

2. **Set up your API key:**
   
   **Easiest method - Use .env file (recommended):**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your API key
   # Mac/Linux/Windows (Git Bash):
   nano .env
   # or
   code .env
   
   # Windows (Command Prompt):
   notepad .env
   
   # Windows (PowerShell):
   notepad .env
   ```
   
   Then edit `.env` and replace `your-api-key-here` with your actual API key:
   ```
   ELEVENLABS_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
   ```
   
   **Alternative - Set environment variable manually:**
   
   **Mac/Linux:**
   ```bash
   export ELEVENLABS_API_KEY="your-api-key-here"
   export ELEVENLABS_VOICE_ID="EXAVITQu4vr4xnSDxMaL"  # Optional: Default is "Bella" (natural female voice)
   ```
   
   **Windows (Command Prompt):**
   ```cmd
   set ELEVENLABS_API_KEY=your-api-key-here
   set ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
   ```
   
   **Windows (PowerShell):**
   ```powershell
   $env:ELEVENLABS_API_KEY="your-api-key-here"
   $env:ELEVENLABS_VOICE_ID="EXAVITQu4vr4xnSDxMaL"
   ```

3. **Start the servers** (the voice service will automatically be used if the API key is set)

**Note:** 
- The `.env` file is automatically loaded when you start the Flask server
- If no API key is set, the chatbot will automatically fall back to browser-based text-to-speech (still optimized for natural female voices)
- The `.env` file is already in `.gitignore`, so your API key won't be committed to git

## 📋 Detailed Instructions

### 1. Activate Virtual Environment

**Mac/Linux:**
```bash
source .venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

### 2. Start Servers

**Option A: Simple (recommended) - Mac/Linux/Windows (Git Bash)**
```bash
./start.sh
```

**Option B: Manual - Mac/Linux**
```bash
# Terminal 1: Start Rasa
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
rasa run --enable-api --cors "*"

# Terminal 2: Start Flask
python app.py
```

**Option B: Manual - Windows (Command Prompt)**
```cmd
REM Terminal 1: Start Rasa
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set VECLIB_MAXIMUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
rasa run --enable-api --cors "*"

REM Terminal 2: Start Flask
python app.py
```

**Option B: Manual - Windows (PowerShell)**
```powershell
# Terminal 1: Start Rasa
$env:OPENBLAS_NUM_THREADS=1
$env:OMP_NUM_THREADS=1
$env:MKL_NUM_THREADS=1
$env:VECLIB_MAXIMUM_THREADS=1
$env:NUMEXPR_NUM_THREADS=1
rasa run --enable-api --cors "*"

# Terminal 2: Start Flask
python app.py
```

### 3. Training

**Mac/Linux/Windows (Git Bash):**
```bash
# Train only
rasa train

# Train and start
./train_and_run.sh
```

**Windows (Command Prompt/PowerShell):**
```cmd
REM Train only
rasa train

REM Then start manually (see Option B above)
```

### 4. Stop Servers

**Mac/Linux/Windows (Git Bash):**
```bash
./stop.sh
```

**Windows (EASIEST - using batch file):**
```cmd
stop.bat
```

**Windows (Command Prompt - manual):**
```cmd
taskkill /F /IM python.exe /FI "WINDOWTITLE eq rasa*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq app.py*" 2>nul
```

**Windows (PowerShell - manual):**
```powershell
Get-Process python | Where-Object {$_.CommandLine -like "*rasa*"} | Stop-Process -Force
Get-Process python | Where-Object {$_.CommandLine -like "*app.py*"} | Stop-Process -Force
```

**Manual (all platforms):**
- Press `Ctrl+C` in both terminals

## 🌐 Access

- **Chatbot UI:** http://localhost:5001
- **Rasa API:** http://localhost:5005

## 📁 Project Structure

```
stayassist/
├── actions/              # Custom Rasa actions
│   ├── actions.py        # Validation and logic
│   └── action_ask_guests.py
├── data/                 # Rasa training data
│   ├── flows.yml         # Conversation flows
│   ├── nlu.yml          # Intent examples
│   └── patterns.yml     # Pattern matching
├── domain.yml           # Rasa domain configuration
├── config.yml           # Rasa pipeline configuration
├── app.py               # Flask backend server
├── frontend/            # Frontend UI
│   ├── index.html
│   ├── css/
│   └── js/
├── start.sh             # Start everything (Mac/Linux/Git Bash)
├── start.bat            # Start everything (Windows)
├── stop.sh              # Stop everything (Mac/Linux/Git Bash)
├── stop.bat             # Stop everything (Windows)
├── train_and_run.sh     # Train and start (Mac/Linux/Git Bash)
├── train_and_run.bat    # Train and start (Windows)
└── run.sh               # Legacy run script

```

## 🔧 Features

- ✅ Booking flow with slot collection
- ✅ Calendar widget for date selection
- ✅ Facility information (pool, parking, etc.)
- ✅ Accessibility questions
- ✅ Robust question handling during booking
- ✅ Automatic validation and error handling

## 🐛 Troubleshooting

### Port already in use?

**Mac/Linux/Windows (Git Bash):**
```bash
# Stop all servers
./stop.sh

# Wait a moment and start again
./start.sh
```

**Windows (Command Prompt):**
```cmd
REM Find and kill processes using ports 5001 and 5005
netstat -ano | findstr :5001
netstat -ano | findstr :5005
REM Use the PID from above and kill it:
taskkill /PID <PID> /F
```

**Windows (PowerShell):**
```powershell
# Find and kill processes using ports 5001 and 5005
Get-NetTCPConnection -LocalPort 5001,5005 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }
```

### Rasa training errors?

**All platforms:**
```bash
# Check for syntax errors
rasa data validate
```

### Flask errors?

**Mac/Linux/Windows (Git Bash):**
```bash
# Check if Rasa is running
curl http://localhost:5005/status
```

**Windows (Command Prompt):**
```cmd
REM Check if Rasa is running
curl http://localhost:5005/status
```

**Windows (PowerShell):**
```powershell
# Check if Rasa is running
Invoke-WebRequest -Uri http://localhost:5005/status
```

### OpenBLAS crashes (macOS ARM64)?

**Mac:**
```bash
# These environment variables are already set in start.sh
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
```

**Windows:**
```cmd
REM Set environment variables (usually not needed on Windows)
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
set VECLIB_MAXIMUM_THREADS=1
set NUMEXPR_NUM_THREADS=1
```

## 📝 Git Workflow

**All platforms:**
```bash
# Commit and push changes
git add -A
git commit -m "Description of changes"
git push origin main
```

## 💾 Bookings Storage

Bookings are stored persistently in `data/bookings.json`. This file is automatically created when the first booking is made and is excluded from git (see `.gitignore`).

**Location:**
- Mac/Linux/Windows: `data/bookings.json` (relative to project root)

**View bookings:**
```bash
# Mac/Linux/Windows (Git Bash)
cat data/bookings.json

# Windows (Command Prompt)
type data\bookings.json

# Windows (PowerShell)
Get-Content data\bookings.json
```

## 📚 More Info

For more details about Rasa Pro, see: https://rasa.com/docs/rasa/
