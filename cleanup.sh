#!/usr/bin/env bash
set -euo pipefail

# Cleanup script for Linux host.
# It removes compose resources and can optionally remove venv/image artifacts.

# Stop containers and remove compose volumes (including Ollama model data volume).
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
echo "Stopping containers and removing volumes (incl. Ollama data)..."
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
  # Ask before deleting slower-to-rebuild assets.
  read -r -p "Remove $description at '$path'? (y/N) " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "Removing $description..."
    rm -rf "$path"
  else
    echo "Keeping $description."
  fi
}

# Keep this optional, because rebuilding venv can be slow.
confirm_remove "$VENV_PATH" "virtual env"

# Always remove project data directory (requested cleanup policy).
if [ -e "$DATA_PATH" ]; then
  echo "Removing data directory (DB) at '$DATA_PATH'..."
  rm -rf "$DATA_PATH"
else
  echo "Data directory not found; nothing to remove."
fi

# Optionally remove Ollama image to reclaim disk space.
read -r -p "Remove Ollama image '$OLLAMA_IMAGE'? (y/N) " remove_img
if [[ "$remove_img" =~ ^[Yy]$ ]]; then
  echo "Removing Ollama image..."
  docker rmi "$OLLAMA_IMAGE" >/dev/null 2>&1 || true
else
  echo "Keeping Ollama image."
fi

echo "Cleanup complete."
