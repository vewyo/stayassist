#!/bin/bash

# Eenvoudig script om alles te stoppen
# Gebruik: ./stop.sh

echo "🛑 Stoppen van servers..."
pkill -f "rasa run" 2>/dev/null
pkill -f "python.*app.py" 2>/dev/null
sleep 1
echo "✅ Servers gestopt"

