#!/usr/bin/env bash
# Stop web controller tmux session

set -euo pipefail

SESSION_NAME="${SESSION_NAME:-mta-web}"
WEB_RUNTIME_SCRIPT="${WEB_RUNTIME_SCRIPT:-web_control.py}"

echo "🛑 Stopping web controller..."

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "   Sending stop signal..."
    tmux send-keys -t "$SESSION_NAME" C-c
    sleep 1

    echo "   Closing tmux session..."
    tmux kill-session -t "$SESSION_NAME"
else
    echo "⚠️  Session '$SESSION_NAME' is not running."
fi

if pgrep -f "python3 .*${WEB_RUNTIME_SCRIPT}" >/dev/null 2>&1; then
    echo "   Cleaning up orphaned ${WEB_RUNTIME_SCRIPT} processes..."
    pkill -f "python3 .*${WEB_RUNTIME_SCRIPT}" || true
fi

echo "✓ Web controller stopped"
