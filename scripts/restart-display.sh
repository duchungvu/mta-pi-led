#!/usr/bin/env bash
# Restart MTA LED Display

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 Restarting MTA LED Display..."
echo ""

# Stop if running
"$SCRIPT_DIR/stop-display.sh"

# Wait a moment
sleep 2

# Start again
"$SCRIPT_DIR/start-display.sh"
