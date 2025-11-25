#!/bin/bash

# Eenvoudig script om alles te starten
# Gebruik: ./start.sh

echo "🛑 Stoppen van oude servers..."
pkill -f "rasa run" 2>/dev/null
pkill -f "python.*app.py" 2>/dev/null
sleep 2

echo "📚 Activeren van virtual environment..."
source .venv/bin/activate

echo "🚀 Starten van Rasa server..."
rasa run --enable-api --cors "*" &
RASA_PID=$!

echo "⏳ Wachten tot Rasa is gestart..."
sleep 8

echo "🚀 Starten van Flask server..."
python app.py &
FLASK_PID=$!

echo ""
echo "✅ Klaar! Servers draaien:"
echo "   - Rasa: http://localhost:5005"
echo "   - Chatbot: http://localhost:5001"
echo ""
echo "Druk op Ctrl+C om te stoppen"

# Wacht tot gebruiker stopt
wait

