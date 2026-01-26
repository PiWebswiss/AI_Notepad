#!/usr/bin/env bash
set -e

# Seed DB if missing/empty, then run the Tk app. No DB writes after seeding.
DB_FILE="${DB_FILE:-/data/ainotepad_vocab.db}"

echo "Checking SQLite vocab at $DB_FILE..."
python /app/seed_db.py

# Decide how to launch Tk: native display or headless Xvfb fallback
# If user asked for native (HEADLESS=0) but DISPLAY is empty, try a sensible default (:0)
if [ "${HEADLESS:-0}" = "0" ] && [ -z "${DISPLAY:-}" ]; then
  export DISPLAY=:0
  echo "DISPLAY not set; defaulting to :0 for native X display."
fi

RUNNER=""
python - <<'PY'
import sys
try:
    import tkinter as tk
    tk.Tk().destroy()
    sys.exit(0)
except Exception as e:
    print(f"Display test failed: {e}")
    sys.exit(1)
PY
if [ $? -ne 0 ]; then
  echo "Falling back to headless mode (xvfb-run)..."
  RUNNER="xvfb-run -a"
fi

if [ "${HEADLESS:-0}" = "1" ]; then
  echo "HEADLESS=1 set; using Xvfb."
  RUNNER="xvfb-run -a"
fi

echo "Starting AI Notepad..."
if [ "$RUNNER" = "xvfb-run -a" ]; then
  # Avoid inheriting a broken host DISPLAY when using Xvfb
  unset DISPLAY
fi
exec $RUNNER python app.py
