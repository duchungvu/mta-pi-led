#!/usr/bin/env bash
# Stop MTA LED Display tmux session

set -euo pipefail

SESSION_NAME="${SESSION_NAME:-mta-display}"

echo "🛑 Stopping MTA LED Display..."

# Check if session exists
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "⚠️  Session '$SESSION_NAME' is not running."
    exit 0
fi

# Send Ctrl+C to stop the Python program gracefully
echo "   Sending stop signal..."
tmux send-keys -t "$SESSION_NAME" C-c

# Wait a moment for graceful shutdown
sleep 1

# Kill the session
echo "   Closing tmux session..."
tmux kill-session -t "$SESSION_NAME"

echo "✓ MTA display stopped"
echo ""
echo "📋 To start again:"
echo "   ./scripts/start-display.sh"
