#!/bin/bash

# Simple script to start everything
# Usage: ./start.sh

echo "Stopping old servers..."
pkill -f "rasa run" 2>/dev/null
pkill -f "python.*app.py" 2>/dev/null
sleep 2

echo "Activating virtual environment..."
source .venv/bin/activate

# Fix for OpenBLAS crashes on macOS ARM64
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

echo "Starting Rasa server..."
rasa run --enable-api --cors "*" &
RASA_PID=$!

echo "Waiting for Rasa to start..."
sleep 8

echo "Starting Flask server..."
python app.py &
FLASK_PID=$!

echo ""
echo "Done! Servers running:"
echo "   - Rasa: http://localhost:5005"
echo "   - Chatbot: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop"

# Wait until user stops
wait
