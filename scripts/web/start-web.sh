#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
APP_DIR="$PROJECT_DIR/src"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_DIR"

# Activate virtual environment
if [ -f "$VENV_DIR/bin/activate" ]; then
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "⚠️  Virtualenv not found at $VENV_DIR. Continuing without activation."
fi

# Start Flask app in background
cd "$APP_DIR"
"$PYTHON_BIN" app.py &
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
