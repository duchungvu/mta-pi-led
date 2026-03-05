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

# Clean up orphaned board processes that may have been started outside tmux.
if pgrep -f "python3 .*led_board.py" >/dev/null 2>&1; then
    echo "   Cleaning up orphaned led_board.py processes..."
    sudo pkill -f "python3 .*led_board.py" || true
fi

echo "✓ MTA display stopped"
echo ""
echo "📋 To start again:"
echo "   ./scripts/board/start.sh"
