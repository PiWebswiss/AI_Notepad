#!/usr/bin/env pwsh
# Define variable `ErrorActionPreference` so later commands can reuse this value.
$ErrorActionPreference = "Stop"

# Launch AI Notepad locally (native Tk window) while Ollama + DB stay in Docker.
# - Starts/pulls Ollama as needed.
# - Sets up a venv, installs deps, seeds the DB under ./data, then runs the app.

# Define variable `root` so later commands can reuse this value.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
# Execute `Set-Location` for this setup/cleanup action.
Set-Location $root
# Define variable `appDir` so later commands can reuse this value.
$appDir = Join-Path $root "app"

# Resolve OLLAMA_MODEL (default gemma3:1b)
# Define variable `model` so later commands can reuse this value.
$model = $env:OLLAMA_MODEL
# Check this condition before executing the PowerShell branch.
if (-not $model -and (Test-Path ".env")) {
  # Define variable `line` so later commands can reuse this value.
  $line = Get-Content ".env" | Where-Object { $_ -like "OLLAMA_MODEL=*" } | Select-Object -Last 1
  # Check this condition before executing the PowerShell branch.
  if ($line) { $model = $line.Substring("OLLAMA_MODEL=".Length) }
# Close the current script block scope.
}
# Check this condition before executing the PowerShell branch.
if (-not $model) { $model = "gemma3:1b" }

# Execute `Write-Host` for this setup/cleanup action.
Write-Host "Starting Ollama container..."
# Execute `docker` for this setup/cleanup action.
docker compose up -d ollama

# Pull model if missing
# Execute `Write-Host` for this setup/cleanup action.
Write-Host "Ensuring model '$model' is available in Ollama..."
# Define variable `names` so later commands can reuse this value.
$names = @()
# Repeat this block for retries or item-by-item processing.
for ($i = 0; $i -lt 20; $i++) {
  # Wrap potentially failing commands with explicit error handling.
  try {
    # Define variable `list` so later commands can reuse this value.
    $list = docker compose exec -T ollama ollama list 2>$null
    # Check this condition before executing the PowerShell branch.
    if ($LASTEXITCODE -eq 0 -and $list) {
      # Close the current script block scope.
      $names = $list -split "`n" | Select-Object -Skip 1 | ForEach-Object { ($_ -split "\s+")[0] }
      # Execute `break` for this setup/cleanup action.
      break
    # Close the current script block scope.
    }
  # Close the current script block scope.
  } catch { }
  # Execute `Start-Sleep` for this setup/cleanup action.
  Start-Sleep -Seconds 1
# Close the current script block scope.
}
# Check this condition before executing the PowerShell branch.
if ($names -notcontains $model) {
  # Execute `Write-Host` for this setup/cleanup action.
  Write-Host "Pulling $model into Ollama..."
  # Execute `docker` for this setup/cleanup action.
  docker compose exec -T ollama ollama pull $model
# Close the current script block scope.
}

# Venv setup
# Define variable `venvPath` so later commands can reuse this value.
$venvPath = Join-Path $root ".venv"
# Define variable `pythonDir` so later commands can reuse this value.
$pythonDir = Join-Path $venvPath "Scripts"
# Define variable `python` so later commands can reuse this value.
$python = Join-Path $pythonDir "python.exe"
# Check this condition before executing the PowerShell branch.
if (-not (Test-Path $venvPath)) {
  # Execute `Write-Host` for this setup/cleanup action.
  Write-Host "Creating venv at $venvPath"
  # Check this condition before executing the PowerShell branch.
  if (Get-Command python -ErrorAction SilentlyContinue) {
    # Execute `python` for this setup/cleanup action.
    python -m venv $venvPath
  # Execute `}` for this setup/cleanup action.
  } else {
    # Execute `py` for this setup/cleanup action.
    py -3 -m venv $venvPath
  # Close the current script block scope.
  }
# Close the current script block scope.
}

# Execute `Write-Host` for this setup/cleanup action.
Write-Host "Installing Python dependencies..."
# Execute `&` for this setup/cleanup action.
& $python -m pip install --upgrade pip
# Execute `&` for this setup/cleanup action.
& $python -m pip install -r (Join-Path $appDir "requirements.txt")

# App environment
# Execute `$env:DB_FILE` for this setup/cleanup action.
$env:DB_FILE = Join-Path (Join-Path $root "data") "ainotepad_vocab.db"
# Execute `$env:OLLAMA_HOST` for this setup/cleanup action.
$env:OLLAMA_HOST = "http://localhost:11434"
# Execute `New-Item` for this setup/cleanup action.
New-Item -ItemType Directory -Force -Path (Split-Path $env:DB_FILE) | Out-Null

# Execute `Write-Host` for this setup/cleanup action.
Write-Host "Seeding vocab DB at $env:DB_FILE (runs only if needed)..."
# Execute `&` for this setup/cleanup action.
& $python (Join-Path $appDir "seed_db.py")

# Execute `Write-Host` for this setup/cleanup action.
Write-Host "Starting AI Notepad locally..."
# Execute `&` for this setup/cleanup action.
& $python (Join-Path $appDir "app.py")
