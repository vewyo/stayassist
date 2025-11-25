#!/bin/bash

# Simple script to stop everything
# Usage: ./stop.sh

echo "Stopping servers..."
pkill -f "rasa run" 2>/dev/null
pkill -f "python.*app.py" 2>/dev/null
sleep 1
echo "Servers stopped"
