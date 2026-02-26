#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

# Stop containers and remove compose volumes (including Ollama model data volume).
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
Write-Host "Stopping containers and removing volumes (incl. Ollama data)..."
docker compose down -v

$venvPath = Join-Path $root ".venv"
$dataPath = Join-Path $root "data"
$ollamaImage = "ollama/ollama:latest"

function Confirm-Remove($path, $description) {
  if (-not (Test-Path $path)) { return }
  $answer = Read-Host "Remove $description at '$path'? (y/N)"
  if ($answer -match '^[Yy]$') {
    Write-Host "Removing $description..."
    Remove-Item -Recurse -Force $path
  } else {
    Write-Host "Keeping $description."
  }
}

# Keep this optional, because rebuilding venv can be slow.
Confirm-Remove $venvPath "virtual env"

# Always remove project data directory (requested cleanup policy).
if (Test-Path $dataPath) {
  Write-Host "Removing data directory (DB) at '$dataPath'..."
  Remove-Item -Recurse -Force $dataPath
} else {
  Write-Host "Data directory not found; nothing to remove."
}

# Optionally remove Ollama image to reclaim disk space.
$removeImg = Read-Host "Remove Ollama image '$ollamaImage'? (y/N)"
if ($removeImg -match '^[Yy]$') {
  Write-Host "Removing Ollama image..."
  docker rmi $ollamaImage 2>$null | Out-Null
} else {
  Write-Host "Keeping Ollama image."
}

Write-Host "Cleanup complete."
