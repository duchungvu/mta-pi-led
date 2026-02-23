#!/usr/bin/env bash
# Attach to the running MTA LED Display tmux session

set -euo pipefail

SESSION_NAME="${SESSION_NAME:-mta-display}"

echo "📺 Connecting to MTA LED Display..."

# Check if session exists
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "❌ Session '$SESSION_NAME' is not running."
    echo ""
    echo "📋 To start the display:"
    echo "   ./scripts/board/start.sh"
    exit 1
fi

echo "✓ Attaching to session (Press Ctrl+B then D to detach)"
sleep 1

# Attach to the session
tmux attach -t "$SESSION_NAME"
