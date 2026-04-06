#!/usr/bin/env bash
set -euo pipefail

# Generic remote script runner — executes any project script on the Pi via SSH.
# Usage: ./scripts/pi-run.sh <script-path> [args...]
# Example: ./scripts/pi-run.sh web/start.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/pi-env.sh"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <script-path> [args...]" >&2
  echo "Example: $0 web/start.sh" >&2
  exit 1
fi

SCRIPT_PATH="$1"
shift

ssh "${PI_USER}@${PI_HOST}" "cd '${PI_DIR}' && ./scripts/${SCRIPT_PATH} $*"
