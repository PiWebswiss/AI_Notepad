#!/usr/bin/env bash
# This file was developed with the assistance of OpenAI Codex (ChatGPT).
# Exit immediately on error, treat unset variables as errors, propagate pipe failures.
set -euo pipefail

# Cleanup script for Linux host.
# Removes Docker containers/volumes and optionally local artifacts (venv, DB, image).

# Resolve project root from the script's own location (works regardless of working directory).
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "Stopping containers and removing volumes (incl. Ollama data)..."
# -v also removes named volumes declared in docker-compose.yml (Ollama model cache).
docker compose down -v

VENV_PATH="$ROOT/.venv"
DATA_PATH="$ROOT/data"
OLLAMA_IMAGE="ollama/ollama:latest"

confirm_remove() {
  local path="$1"
  local description="$2"
  if [ ! -e "$path" ]; then
    return
  fi
  # Prompt before deleting assets that are slow to rebuild (e.g. venv).
  read -r -p "Remove $description at '$path'? (y/N) " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "Removing $description..."
    rm -rf "$path"
  else
    echo "Keeping $description."
  fi
}

# The venv takes time to recreate (pip install), so ask before removing.
confirm_remove "$VENV_PATH" "virtual env"

# Remove the legacy root-level pip-install sentinel if it exists.
# Current versions place the sentinel inside .venv, so it is deleted with the venv;
# this line cleans up orphans left behind by older installations.
LEGACY_SENTINEL="$ROOT/.deps-installed"
if [ -f "$LEGACY_SENTINEL" ]; then rm -f "$LEGACY_SENTINEL"; fi

# The data directory holds the SQLite vocab DB — always removed on cleanup.
if [ -e "$DATA_PATH" ]; then
  echo "Removing data directory (DB) at '$DATA_PATH'..."
  rm -rf "$DATA_PATH"
else
  echo "Data directory not found; nothing to remove."
fi

# The Ollama image is several GB; ask before removing to avoid a long re-download.
read -r -p "Remove Ollama image '$OLLAMA_IMAGE'? (y/N) " remove_img
if [[ "$remove_img" =~ ^[Yy]$ ]]; then
  echo "Removing Ollama image..."
  # Suppress output; errors are non-fatal (image may already be removed).
  docker rmi "$OLLAMA_IMAGE" >/dev/null 2>&1 || true
else
  echo "Keeping Ollama image."
fi

# Remove the desktop shortcut created by run.sh on first launch.
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
SHORTCUT_FILE="$DESKTOP_DIR/ai-notepad.desktop"
if [ -f "$SHORTCUT_FILE" ]; then
  echo "Removing desktop shortcut..."
  rm -f "$SHORTCUT_FILE"
fi

echo "Cleanup complete."
