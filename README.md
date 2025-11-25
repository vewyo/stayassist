# StayAssist Chatbot

Een intelligente chatbot voor hotelboekingen met Rasa Pro en Flask.

## 🚀 Quick Start

### Vereisten
- Python 3.8+
- Virtual environment (`.venv`)

### Eenvoudige Commands

```bash
# Alles stoppen (als er servers draaien)
./stop.sh

# Alles starten
./start.sh

# Trainen en daarna starten
./train_and_run.sh
```

## 📋 Gedetailleerde Instructies

### 1. Virtual Environment Activeren

```bash
source .venv/bin/activate
```

### 2. Servers Starten

**Optie A: Simpel (aanbevolen)**
```bash
./start.sh
```

**Optie B: Handmatig**
```bash
# Terminal 1: Start Rasa
rasa run --enable-api --cors "*"

# Terminal 2: Start Flask
python app.py
```

### 3. Training

```bash
# Alleen trainen
rasa train

# Trainen en starten
./train_and_run.sh
```

### 4. Servers Stoppen

**Simpel:**
```bash
./stop.sh
```

**Handmatig:**
- Druk `Ctrl+C` in beide terminals

## 🌐 Toegang

- **Chatbot UI:** http://localhost:5001
- **Rasa API:** http://localhost:5005

## 📁 Project Structuur

```
stayassist/
├── actions/              # Custom Rasa actions
│   ├── actions.py        # Validatie en logica
│   └── action_ask_guests.py
├── data/                 # Rasa training data
│   ├── flows.yml         # Conversatie flows
│   ├── nlu.yml          # Intent voorbeelden
│   └── patterns.yml     # Pattern matching
├── domain.yml           # Rasa domain configuratie
├── config.yml           # Rasa pipeline configuratie
├── app.py               # Flask backend server
├── frontend/            # Frontend UI
│   ├── index.html
│   ├── css/
│   └── js/
├── start.sh             # Start alles (simpel)
├── stop.sh              # Stop alles (simpel)
├── train_and_run.sh     # Train en start
└── run.sh               # Oude run script

```

## 🔧 Features

- ✅ Booking flow met slot collection
- ✅ Calendar widget voor datum selectie
- ✅ Facility informatie (pool, parking, etc.)
- ✅ Accessibility vragen
- ✅ Robuuste vraag handling tijdens booking
- ✅ Automatische validatie en foutafhandeling

## 🐛 Troubleshooting

### Poort al in gebruik?

```bash
# Stop alle servers
./stop.sh

# Wacht even en start opnieuw
./start.sh
```

### Rasa training errors?

```bash
# Check voor syntax errors
rasa data validate
```

### Flask errors?

```bash
# Check of Rasa draait
curl http://localhost:5005/status
```

## 📝 Git Workflow

```bash
# Wijzigingen committen en pushen
git add -A
git commit -m "Beschrijving van wijzigingen"
git push origin main
```

## 📚 Meer Info

Voor meer details over Rasa Pro, zie: https://rasa.com/docs/rasa/
