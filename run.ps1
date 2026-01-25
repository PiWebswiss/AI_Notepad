#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"

# If you are using an X server (e.g., VcXsrv), this is the usual DISPLAY.
if (-not $env:DISPLAY) {
  $env:DISPLAY = "host.docker.internal:0.0"
}

docker compose down

$model = $env:OLLAMA_MODEL
if (-not $model -and (Test-Path ".env")) {
  $line = Get-Content ".env" | Where-Object { $_ -like "OLLAMA_MODEL=*" } | Select-Object -Last 1
  if ($line) {
    $model = $line.Substring("OLLAMA_MODEL=".Length)
  }
}
if (-not $model) {
  $model = "gemma3:1b"
}

if ($env:NO_AUTO_PULL -ne "1") {
  docker compose up -d ollama

  $list = $null
  for ($i = 0; $i -lt 20; $i++) {
    try {
      $list = docker compose exec -T ollama ollama list 2>$null
      if ($LASTEXITCODE -eq 0) { break }
    } catch {
    }
    Start-Sleep -Seconds 1
  }

  if ($list) {
    $names = $list -split "`n" | Select-Object -Skip 1 | ForEach-Object { ($_ -split "\s+")[0] }
    if ($names -notcontains $model) {
      Write-Host "Model $model not found; pulling once via ollama_init..."
      docker compose --profile init run --rm ollama_init
    }
  } else {
    Write-Host "Ollama not ready; skipping auto model pull."
  }
}

docker compose up --build
