#!/usr/bin/env pwsh
# Define variable `ErrorActionPreference` so later commands can reuse this value.
$ErrorActionPreference = "Stop"

# Stop supporting containers and optionally remove local artifacts (venv/data).

# Define variable `root` so later commands can reuse this value.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
# Execute `Set-Location` for this setup/cleanup action.
Set-Location $root

# Execute `Write-Host` for this setup/cleanup action.
Write-Host "Stopping containers and removing volumes (incl. Ollama data)..."
# Execute `docker` for this setup/cleanup action.
docker compose down -v

# Define variable `venvPath` so later commands can reuse this value.
$venvPath = Join-Path $root ".venv"
# Define variable `dataPath` so later commands can reuse this value.
$dataPath = Join-Path $root "data"
# Define variable `ollamaImage` so later commands can reuse this value.
$ollamaImage = "ollama/ollama:latest"

# Define helper function `Confirm-Remove` for reusable script behavior.
function Confirm-Remove($path, $description) {
  # Check this condition before executing the PowerShell branch.
  if (-not (Test-Path $path)) { return }
  # Define variable `answer` so later commands can reuse this value.
  $answer = Read-Host "Remove $description at '$path'? (y/N)"
  # Check this condition before executing the PowerShell branch.
  if ($answer -match '^[Yy]$') {
    # Execute `Write-Host` for this setup/cleanup action.
    Write-Host "Removing $description..."
    # Execute `Remove-Item` for this setup/cleanup action.
    Remove-Item -Recurse -Force $path
  # Execute `}` for this setup/cleanup action.
  } else {
    # Execute `Write-Host` for this setup/cleanup action.
    Write-Host "Keeping $description."
  # Close the current script block scope.
  }
# Close the current script block scope.
}

# Execute `Confirm-Remove` for this setup/cleanup action.
Confirm-Remove $venvPath "virtual env"

# Always remove the DB/data directory (requested)
# Check this condition before executing the PowerShell branch.
if (Test-Path $dataPath) {
  # Execute `Write-Host` for this setup/cleanup action.
  Write-Host "Removing data directory (DB) at '$dataPath'..."
  # Execute `Remove-Item` for this setup/cleanup action.
  Remove-Item -Recurse -Force $dataPath
# Execute `}` for this setup/cleanup action.
} else {
  # Execute `Write-Host` for this setup/cleanup action.
  Write-Host "Data directory not found; nothing to remove."
# Close the current script block scope.
}

# Optionally remove the Ollama image to reclaim space
# Define variable `removeImg` so later commands can reuse this value.
$removeImg = Read-Host "Remove Ollama image '$ollamaImage'? (y/N)"
# Check this condition before executing the PowerShell branch.
if ($removeImg -match '^[Yy]$') {
  # Execute `Write-Host` for this setup/cleanup action.
  Write-Host "Removing Ollama image..."
  # Execute `docker` for this setup/cleanup action.
  docker rmi $ollamaImage 2>$null | Out-Null
# Execute `}` for this setup/cleanup action.
} else {
  # Execute `Write-Host` for this setup/cleanup action.
  Write-Host "Keeping Ollama image."
# Close the current script block scope.
}

# Execute `Write-Host` for this setup/cleanup action.
Write-Host "Cleanup complete."
