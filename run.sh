#!/usr/bin/env bash
# Exit immediately on error, treat unset variables as errors, propagate pipe failures.
set -euo pipefail

# Run AI Notepad locally (native Tk UI), with Ollama in Docker.
# Execution flow:
# 1) offer desktop shortcut on first run
# 2) start Ollama service
# 3) ensure the selected model exists
# 4) prepare Python venv + deps
# 5) seed/migrate SQLite vocab DB
# 6) launch the desktop app

# Resolve the project root from the script's own location (works regardless of working directory).
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
APP_DIR="$ROOT/app"

# Ask about desktop shortcut on first run (actual creation happens at the end, after setup succeeds).
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
SHORTCUT_FILE="$DESKTOP_DIR/ai-notepad.desktop"
CREATE_SHORTCUT=0
if [ -d "$DESKTOP_DIR" ] && [ ! -f "$SHORTCUT_FILE" ]; then
  read -r -p "Create a desktop shortcut for AI Notepad? (y/N) " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    CREATE_SHORTCUT=1
  fi
fi

# Read OLLAMA_MODEL from the environment or from the .env file.
MODEL="${OLLAMA_MODEL:-}"
if [ -z "$MODEL" ] && [ -f .env ]; then
  # Parse the last matching line in .env to support overrides at the bottom of the file.
  MODEL="$(sed -n 's/^OLLAMA_MODEL=//p' .env | tail -n 1)"
fi
# Expose the resolved value so child processes (app) inherit it.
if [ -n "$MODEL" ]; then
  export OLLAMA_MODEL="$MODEL"
fi

echo "Starting Ollama container..."
# --wait blocks until the healthcheck passes, so Ollama is ready to accept commands.
docker compose up -d --wait ollama

# Pull the model if it is not already cached inside the Ollama container.
if [ -n "$MODEL" ]; then
  list_out="$(docker compose exec -T ollama ollama list 2>/dev/null)"
  if ! printf "%s\n" "$list_out" | awk 'NR>1{print $1}' | grep -Fxq "$MODEL"; then
    echo "Model '$MODEL' not found. Downloading..."
    docker compose exec -T ollama ollama pull "$MODEL"
  else
    echo "Model '$MODEL' already available."
  fi
else
  echo "OLLAMA_MODEL not set; skipping auto model pull."
fi

# Create a local virtual environment to keep Python dependencies isolated from the system.
VENV_PATH="$ROOT/.venv"
PYTHON="$VENV_PATH/bin/python"
if [ ! -d "$VENV_PATH" ]; then
  echo "Creating venv at $VENV_PATH"
  python3 -m venv "$VENV_PATH"
fi

# Skip pip install if requirements.txt hasn't changed since the last successful install.
# The sentinel file is touched after a successful install to record the timestamp.
REQ_FILE="$APP_DIR/requirements.txt"
SENTINEL="$ROOT/.deps-installed"
if [ ! -f "$SENTINEL" ] || [ "$REQ_FILE" -nt "$SENTINEL" ]; then
  echo "Installing Python dependencies..."
  # Upgrade pip itself first to avoid warnings about an outdated installer.
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install -r "$REQ_FILE"
  # Record the install time so subsequent runs skip this step.
  touch "$SENTINEL"
else
  echo "Python dependencies already up to date, skipping install."
fi

# DB_FILE tells the app and seed_db.py where to store the SQLite vocabulary database.
export DB_FILE="$ROOT/data/ainotepad_vocab.db"
# OLLAMA_HOST points the Python client at the local Ollama container (default port 11434).
export OLLAMA_HOST="http://localhost:11434"
# Ensure the data directory exists before seed_db.py tries to create the file inside it.
mkdir -p "$(dirname "$DB_FILE")"

# seed_db.py is idempotent: it only populates the DB if tables are empty.
echo "Seeding vocab DB at $DB_FILE (runs only if needed)..."
"$PYTHON" "$APP_DIR/seed_db.py"

# Create the desktop shortcut now that setup completed successfully.
if [ "$CREATE_SHORTCUT" -eq 1 ]; then
  ICON_PNG="$ROOT/images/icon.png"
  cat > "$SHORTCUT_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=AI Notepad
Comment=Launch AI Notepad
Exec=bash "$ROOT/run.sh"
Icon=$ICON_PNG
Terminal=true
Categories=Utility;TextEditor;
EOF
  # Mark as trusted so the desktop environment allows execution.
  chmod +x "$SHORTCUT_FILE"
  echo "Desktop shortcut created."
fi

echo "Starting AI Notepad locally..."
"$PYTHON" "$APP_DIR/ui.py"
