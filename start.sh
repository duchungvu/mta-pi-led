#!/bin/bash
cd /home/hung/mta-pi-led

# Activate virtual environment
source venv/bin/activate

# Start Flask app in background
python app.py &
FLASK_PID=$!

# Wait for Flask to start
sleep 5

# Start ngrok
ngrok http 5000 &
NGROK_PID=$!

# Monitor logs
echo "App running with PID $FLASK_PID, ngrok with PID $NGROK_PID"
echo "Find ngrok URL at http://localhost:4040"

# Wait for either process to exit
wait $FLASK_PID
