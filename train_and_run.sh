#!/bin/bash

# Script to stop Rasa, train, and run
# Usage: ./train_and_run.sh

cd "$(dirname "$0")"

echo "🛑 Stopping Rasa server..."
pkill -f "rasa run" || true
pkill -f "rasa x" || true
sleep 2

echo "📚 Activating virtual environment..."
source .venv/bin/activate || source venv/bin/activate

echo "🏋️ Training Rasa model..."
rasa train

if [ $? -eq 0 ]; then
    echo "✅ Training completed successfully!"
    echo "🚀 Starting servers..."
    ./run.sh
else
    echo "❌ Training failed. Please check the errors above."
    exit 1
fi

