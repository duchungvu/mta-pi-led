#!/usr/bin/env bash
# Attach to web controller tmux session

set -euo pipefail

SESSION_NAME="${SESSION_NAME:-mta-web}"

echo "📺 Attaching to web controller session '$SESSION_NAME'..."
echo "   (Detach with Ctrl+B, then D)"
echo ""

tmux attach -t "$SESSION_NAME"
