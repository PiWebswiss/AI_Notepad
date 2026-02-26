#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

# Run AI Notepad locally (native Tk UI), with Ollama and DB in Docker.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$appDir = Join-Path $root "app"

# Resolve model from env, then .env, else default.
$model = $env:OLLAMA_MODEL
if (-not $model -and (Test-Path ".env")) {
  $line = Get-Content ".env" | Where-Object { $_ -like "OLLAMA_MODEL=*" } | Select-Object -Last 1
  if ($line) { $model = $line.Substring("OLLAMA_MODEL=".Length) }
}
if (-not $model) { $model = "gemma3:1b" }

Write-Host "Starting Ollama container..."
docker compose up -d ollama

# Pull model if it is not already available.
Write-Host "Ensuring model '$model' is available in Ollama..."
$names = @()
for ($i = 0; $i -lt 20; $i++) {
  try {
    $list = docker compose exec -T ollama ollama list 2>$null
    if ($LASTEXITCODE -eq 0 -and $list) {
      $names = $list -split "`n" | Select-Object -Skip 1 | ForEach-Object { ($_ -split "\s+")[0] }
      break
    }
  } catch { }
  Start-Sleep -Seconds 1
}
if ($names -notcontains $model) {
  Write-Host "Pulling $model into Ollama..."
  docker compose exec -T ollama ollama pull $model
}

# Create local venv if needed.
$venvPath = Join-Path $root ".venv"
$pythonDir = Join-Path $venvPath "Scripts"
$python = Join-Path $pythonDir "python.exe"
if (-not (Test-Path $venvPath)) {
  Write-Host "Creating venv at $venvPath"
  if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m venv $venvPath
  } else {
    py -3 -m venv $venvPath
  }
}

Write-Host "Installing Python dependencies..."
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $appDir "requirements.txt")

# Configure app env and seed DB if needed.
$env:DB_FILE = Join-Path (Join-Path $root "data") "ainotepad_vocab.db"
$env:OLLAMA_HOST = "http://localhost:11434"
New-Item -ItemType Directory -Force -Path (Split-Path $env:DB_FILE) | Out-Null

Write-Host "Seeding vocab DB at $env:DB_FILE (runs only if needed)..."
& $python (Join-Path $appDir "seed_db.py")

Write-Host "Starting AI Notepad locally..."
& $python (Join-Path $appDir "app.py")
