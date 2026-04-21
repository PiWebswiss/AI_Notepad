#!/usr/bin/env pwsh
# This file was developed with the assistance of OpenAI Codex (ChatGPT).
# Stop immediately on any error instead of silently continuing.
$ErrorActionPreference = "Stop"

# Cleanup script for Windows host.
# Removes Docker containers/volumes and optionally local artifacts (venv, DB, image, shortcut).

# Resolve project root from the script's own location.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Stopping containers and removing volumes (incl. Ollama data)..."
# -v also removes named volumes declared in docker-compose.yml (Ollama model cache).
docker compose down -v

# Paths to local artifacts that may need cleaning.
$venvPath = Join-Path $root ".venv"
$dataPath = Join-Path $root "data"
# Docker image used by the Ollama service.
$ollamaImage = "ollama/ollama:latest"

function Confirm-Remove($path, $description) {
  if (-not (Test-Path $path)) { return }
  # Prompt before deleting assets that are slow to rebuild (e.g. venv).
  $answer = Read-Host "Remove $description at '$path'? (y/N)"
  if ($answer -match '^[Yy]$') {
    Write-Host "Removing $description..."
    Remove-Item -Recurse -Force $path
  } else {
    Write-Host "Keeping $description."
  }
}

# The venv takes time to recreate (pip install), so ask before removing.
Confirm-Remove $venvPath "virtual env"

# The data directory holds the SQLite vocab DB — always removed on cleanup.
if (Test-Path $dataPath) {
  Write-Host "Removing data directory (DB) at '$dataPath'..."
  Remove-Item -Recurse -Force $dataPath
} else {
  Write-Host "Data directory not found; nothing to remove."
}

# The Ollama image is several GB; ask before removing to avoid a long re-download.
$removeImg = Read-Host "Remove Ollama image '$ollamaImage'? (y/N)"
if ($removeImg -match '^[Yy]$') {
  Write-Host "Removing Ollama image..."
  # Suppress output: rmi prints nothing useful on success, and errors are non-fatal here.
  docker rmi $ollamaImage 2>$null | Out-Null
}
else {
  Write-Host "Keeping Ollama image."
}

# Remove the desktop shortcut created by run.ps1 on first launch.
$shortcutFile = Join-Path ([Environment]::GetFolderPath("Desktop")) "AI Notepad.lnk"
if (Test-Path $shortcutFile) {
  Write-Host "Removing desktop shortcut..."
  Remove-Item -Force $shortcutFile
}
# Also remove the generated .ico file (converted from icon.png by run.ps1).
$iconIco = Join-Path $root "images\icon.ico"
if (Test-Path $iconIco) {
  Write-Host "Removing generated icon..."
  Remove-Item -Force $iconIco
}

Write-Host "Cleanup complete."
