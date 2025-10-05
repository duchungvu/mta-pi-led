#!/usr/bin/env bash
set -euo pipefail

### ====== CONFIGURE ======
PI_USER="hung"                         # your Pi username
PI_HOST="hung-rpi"                     # Pi hostname, or use its IP if needed
PI_DIR="/home/${PI_USER}/mta-pi-led"   # remote folder (same name as project)
RSYNC_BWLIMIT=0                        # limit rsync speed, 0 = unlimited
### ========================

SRC="$(pwd)/"
DEST="${PI_USER}@${PI_HOST}:${PI_DIR}"

EXCLUDES=(
  --exclude ".git"
  --exclude ".venv"
  --exclude "node_modules"
  --exclude ".cache"
  --exclude "dist"
  --exclude "build"
  --exclude "*.pyc"
  --exclude "__pycache__"
)

RSYNC="/usr/bin/rsync"
FSWATCH="$(command -v fswatch || true)"

# Ensure fswatch exists
if [[ -z "${FSWATCH}" ]]; then
  echo "Error: fswatch not installed. Run: brew install fswatch" >&2
  exit 1
fi

# Ensure remote folder exists
ssh "${PI_USER}@${PI_HOST}" "mkdir -p '${PI_DIR}'"

# Initial sync
echo "Initial sync → ${DEST}"
"${RSYNC}" -avz --delete "${EXCLUDES[@]}" "$SRC" "$DEST"

# Watch and sync
echo "Watching for changes… (Ctrl+C to stop)"
"${FSWATCH}" -or . | while read -r _; do
  sleep 0.2
  "${RSYNC}" -az --delete "${EXCLUDES[@]}" "$SRC" "$DEST"
  echo "[`date '+%H:%M:%S'`] synced ✓"
done
