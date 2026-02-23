#!/usr/bin/env bash
# Start MTA LED Display in tmux session

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
SESSION_NAME="${SESSION_NAME:-mta-display}"
RUNTIME_SCRIPT="${RUNTIME_SCRIPT:-led_board.py}"
SCRIPT_PATH="$PROJECT_DIR/src/$RUNTIME_SCRIPT"
BOARD_CONFIG_PATH="${BOARD_CONFIG_PATH:-$PROJECT_DIR/config/board.json}"
ENABLE_RT_PINNING="${ENABLE_RT_PINNING:-1}"
DISPLAY_CPU_CORE="${DISPLAY_CPU_CORE:-3}"
DISPLAY_RT_PRIORITY="${DISPLAY_RT_PRIORITY:-50}"

echo "🚇 Starting MTA LED Display..."

# Check if session already exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "⚠️  Session '$SESSION_NAME' already exists!"
    echo "   Options:"
    echo "   1. Stop it first: ./scripts/board/stop.sh"
    echo "   2. Attach to it: tmux attach -t $SESSION_NAME"
    exit 1
fi

# Check if Python script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: $SCRIPT_PATH not found!"
    exit 1
fi

# Check if board config exists
if [ ! -f "$BOARD_CONFIG_PATH" ]; then
    echo "❌ Error: board config not found at $BOARD_CONFIG_PATH"
    exit 1
fi

LAUNCH_CMD="sudo env BOARD_CONFIG_PATH='$BOARD_CONFIG_PATH' python3 '$RUNTIME_SCRIPT'"
if [ "$ENABLE_RT_PINNING" = "1" ]; then
    if command -v taskset >/dev/null 2>&1 && command -v chrt >/dev/null 2>&1; then
        LAUNCH_CMD="sudo env BOARD_CONFIG_PATH='$BOARD_CONFIG_PATH' chrt -f '$DISPLAY_RT_PRIORITY' taskset -c '$DISPLAY_CPU_CORE' python3 '$RUNTIME_SCRIPT'"
        echo "⚙️  Launch mode: RT pinned (core=$DISPLAY_CPU_CORE, prio=$DISPLAY_RT_PRIORITY)"
    else
        echo "⚠️  taskset/chrt not available; falling back to standard launch"
    fi
else
    echo "⚙️  Launch mode: standard (ENABLE_RT_PINNING=0)"
fi

# Create new tmux session and run the display
tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_DIR"
tmux send-keys -t "$SESSION_NAME" "cd '$PROJECT_DIR/src'" C-m
tmux send-keys -t "$SESSION_NAME" "$LAUNCH_CMD" C-m

echo "✓ MTA display started in tmux session '$SESSION_NAME'"
echo ""
echo "📋 Useful commands:"
echo "   View display:  tmux attach -t $SESSION_NAME"
echo "   Detach:        Press Ctrl+B, then D"
echo "   Stop display:  ./scripts/board/stop.sh"
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
