#!/bin/bash
# Start MTA LED Display in tmux session

SESSION_NAME="mta-display"
PROJECT_DIR="/home/hung/mta-pi-led"
SCRIPT_PATH="$PROJECT_DIR/src/image_display.py"

echo "🚇 Starting MTA LED Display..."

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "⚠️  Session '$SESSION_NAME' already exists!"
    echo "   Options:"
    echo "   1. Stop it first: ./scripts/stop-display.sh"
    echo "   2. Attach to it: tmux attach -t $SESSION_NAME"
    exit 1
fi

# Check if Python script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: $SCRIPT_PATH not found!"
    exit 1
fi

# Create new tmux session and run the display
tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION_NAME" "cd $PROJECT_DIR/src" C-m
tmux send-keys -t "$SESSION_NAME" "sudo python3 image_display.py" C-m

echo "✓ MTA display started in tmux session '$SESSION_NAME'"
echo ""
echo "📋 Useful commands:"
echo "   View display:  tmux attach -t $SESSION_NAME"
echo "   Detach:        Press Ctrl+B, then D"
echo "   Stop display:  ./scripts/stop-display.sh"
echo ""
echo "🔍 Checking status in 2 seconds..."
sleep 2

# Check if still running
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "✓ Display is running!"
    echo ""
    echo "📺 To see the display output:"
    echo "   tmux attach -t $SESSION_NAME"
else
    echo "❌ Display failed to start. Check for errors."
    exit 1
fi

