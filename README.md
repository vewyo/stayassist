# StayAssist Chatbot

An intelligent chatbot for hotel bookings built with Rasa Pro and Flask.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment (`.venv`)

### Simple Commands

```bash
# Stop everything (if servers are running)
./stop.sh

# Start everything
./start.sh

# Train and then start
./train_and_run.sh
```

## 📋 Detailed Instructions

### 1. Activate Virtual Environment

```bash
source .venv/bin/activate
```

### 2. Start Servers

**Option A: Simple (recommended)**
```bash
./start.sh
```

**Option B: Manual**
```bash
# Terminal 1: Start Rasa
rasa run --enable-api --cors "*"

# Terminal 2: Start Flask
python app.py
```

### 3. Training

   ```bash
# Train only
   rasa train

# Train and start
./train_and_run.sh
```

### 4. Stop Servers

**Simple:**
```bash
./stop.sh
```

**Manual:**
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
├── start.sh             # Start everything (simple)
├── stop.sh              # Stop everything (simple)
├── train_and_run.sh     # Train and start
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

```bash
# Stop all servers
./stop.sh

# Wait a moment and start again
./start.sh
```

### Rasa training errors?

```bash
# Check for syntax errors
rasa data validate
```

### Flask errors?

   ```bash
# Check if Rasa is running
curl http://localhost:5005/status
   ```

## 📝 Git Workflow

   ```bash
# Commit and push changes
git add -A
git commit -m "Description of changes"
git push origin main
```

## 📚 More Info

For more details about Rasa Pro, see: https://rasa.com/docs/rasa/
