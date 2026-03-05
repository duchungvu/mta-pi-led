#!/usr/bin/env bash
# Start web controller in a tmux session

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
SESSION_NAME="${SESSION_NAME:-mta-web}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
APP_DIR="$PROJECT_DIR/src"
PYTHON_BIN="${PYTHON_BIN:-python3}"
WEB_RUNTIME_SCRIPT="${WEB_RUNTIME_SCRIPT:-web_control.py}"
WEB_PORT="${WEB_PORT:-5000}"
WEB_DEBUG="${WEB_DEBUG:-0}"
WEB_RELOADER="${WEB_RELOADER:-0}"
ENABLE_NGROK="${ENABLE_NGROK:-0}"

SCRIPT_PATH="$APP_DIR/$WEB_RUNTIME_SCRIPT"

echo "🌐 Starting web controller..."

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "⚠️  Session '$SESSION_NAME' already exists!"
    echo "   Options:"
    echo "   1. Stop it first: ./scripts/web/stop.sh"
    echo "   2. Attach to it: tmux attach -t $SESSION_NAME"
    exit 1
fi

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: $SCRIPT_PATH not found!"
    exit 1
fi

VENV_ACTIVATE_PATH="$VENV_DIR/bin/activate"
LAUNCH_CMD="cd '$APP_DIR'"
if [ -f "$VENV_ACTIVATE_PATH" ]; then
    LAUNCH_CMD+=" && source '$VENV_ACTIVATE_PATH'"
else
    LAUNCH_CMD+=" && echo '⚠️  Virtualenv not found at $VENV_DIR. Continuing without activation.'"
fi
LAUNCH_CMD+=" && WEB_PORT='$WEB_PORT' WEB_DEBUG='$WEB_DEBUG' WEB_RELOADER='$WEB_RELOADER' '$PYTHON_BIN' '$WEB_RUNTIME_SCRIPT'"

tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION_NAME" "$LAUNCH_CMD" C-m

if [ "$ENABLE_NGROK" = "1" ]; then
    tmux new-window -t "$SESSION_NAME" -n ngrok -c "$PROJECT_DIR"
    tmux send-keys -t "$SESSION_NAME:ngrok" "ngrok http '$WEB_PORT'" C-m
fi

echo "✓ Web controller started in tmux session '$SESSION_NAME'"
echo ""
echo "📋 Useful commands:"
echo "   View logs:     tmux attach -t $SESSION_NAME"
echo "   Detach:        Press Ctrl+B, then D"
echo "   Stop web app:  ./scripts/web/stop.sh"
echo ""
echo "🌍 Expected URL: http://localhost:$WEB_PORT"
if [ "$ENABLE_NGROK" = "1" ]; then
    echo "🌐 ngrok UI: http://localhost:4040"
fi
