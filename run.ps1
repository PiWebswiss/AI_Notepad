#!/usr/bin/env pwsh
# Stop immediately on any error instead of silently continuing.
$ErrorActionPreference = "Stop"

# Run AI Notepad locally (native Tk UI), with Ollama and DB in Docker.
# Execution flow:
# 1) offer desktop shortcut on first run
# 2) start Ollama service
# 3) ensure the selected model exists
# 4) prepare Python venv + deps
# 5) seed/migrate SQLite vocab DB
# 6) launch the desktop app

# Resolve the project root from the script's own location (works regardless of working directory).
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
# Directory containing the Python application source files.
$appDir = Join-Path $root "app"

# Ask about desktop shortcut on first run (actual creation happens at the end, after setup succeeds).
$shortcutFile = Join-Path ([Environment]::GetFolderPath("Desktop")) "AI Notepad.lnk"
$createShortcut = $false
if (-not (Test-Path $shortcutFile)) {
    $ans = Read-Host "Create a desktop shortcut for AI Notepad? (y/N)"
    if ($ans -match '^[Yy]$') { $createShortcut = $true }
}

# Read OLLAMA_MODEL from the environment or from the .env file.
# The default model is not set here — app/ui.py is responsible for the fallback.
$model = $env:OLLAMA_MODEL
if (-not $model -and (Test-Path ".env")) {
  # Parse the last matching line in .env to support overrides at the bottom of the file.
  $line = Get-Content ".env" | Where-Object { $_ -like "OLLAMA_MODEL=*" } | Select-Object -Last 1
  if ($line) { $model = $line.Substring("OLLAMA_MODEL=".Length) }
}
# Expose the resolved value so child processes inherit it.
if ($model) { $env:OLLAMA_MODEL = $model }

# Auto-detect NVIDIA GPU: switch the container runtime to 'nvidia' only when
# both the host driver (nvidia-smi) and the NVIDIA container runtime are
# registered with Docker. DOCKER_RUNTIME is consumed via ${DOCKER_RUNTIME:-runc}
# in docker-compose.yml, so CPU-only hosts fall back to the default runtime.
$gpuAvailable = $false
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
  $runtimes = docker info --format '{{json .Runtimes}}' 2>$null
  if ($runtimes -match 'nvidia') { $gpuAvailable = $true }
}
if ($gpuAvailable) {
  $env:DOCKER_RUNTIME = "nvidia"
  Write-Host "NVIDIA GPU detected - enabling GPU acceleration for Ollama."
} else {
  Write-Host "No NVIDIA GPU detected - Ollama will run on CPU."
}

Write-Host "Starting Ollama container..."
# --wait blocks until the healthcheck passes, so Ollama is ready to accept commands.
docker compose up -d --wait ollama

# Pull the model if it is not already cached inside the Ollama container.
if ($model) {
  $list = docker compose exec -T ollama ollama list 2>$null
  # Skip header line, then extract the first whitespace-delimited column (model name).
  $names = $list -split "`n" | Select-Object -Skip 1 | ForEach-Object { ($_ -split "\s+")[0] }
  if ($names -notcontains $model) {
    Write-Host "Model '$model' not found. Downloading..."
    docker compose exec -T ollama ollama pull $model
  } else {
    Write-Host "Model '$model' already available."
  }
} else {
  Write-Host "OLLAMA_MODEL not set; skipping auto model pull."
}

# Create a local virtual environment to keep Python dependencies isolated from the system.
# Paths to the virtual environment directory and its Python executable.
$venvPath = Join-Path $root ".venv"
$pythonDir = Join-Path $venvPath "Scripts"
$python = Join-Path $pythonDir "python.exe"
if (-not (Test-Path $venvPath)) {
  Write-Host "Creating venv at $venvPath"
  # Try 'python' first; fall back to 'py -3' on machines where only the launcher is in PATH.
  if (Get-Command python -ErrorAction SilentlyContinue) {
    python -m venv $venvPath
  } else {
    py -3 -m venv $venvPath
  }
}

# Skip pip install if requirements.txt hasn't changed since the last successful install.
# The sentinel file is touched after a successful install to record the timestamp.
$reqFile = Join-Path $appDir "requirements.txt"
$sentinel = Join-Path $root ".deps-installed"
if (-not (Test-Path $sentinel) -or (Get-Item $reqFile).LastWriteTime -gt (Get-Item $sentinel).LastWriteTime) {
  Write-Host "Installing Python dependencies..."
  # Upgrade pip itself first to avoid warnings about an outdated installer.
  & $python -m pip install --upgrade pip
  & $python -m pip install -r $reqFile
  if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
  # Record the install time so subsequent runs skip this step.
  New-Item -ItemType File -Force -Path $sentinel | Out-Null
} else {
  Write-Host "Python dependencies already up to date, skipping install."
}

# DB_FILE tells ui.py and seed_db.py where to store the SQLite vocabulary database.
$env:DB_FILE = Join-Path (Join-Path $root "data") "ainotepad_vocab.db"
# OLLAMA_HOST points the Python client at the local Ollama container (default port 11434).
$env:OLLAMA_HOST = "http://localhost:11434"
# Ensure the data directory exists before seed_db.py tries to create the file inside it.
New-Item -ItemType Directory -Force -Path (Split-Path $env:DB_FILE) | Out-Null

# seed_db.py is idempotent: it only populates the DB if tables are empty.
Write-Host "Seeding vocab DB at $env:DB_FILE (runs only if needed)..."
& $python (Join-Path $appDir "seed_db.py")

# Create the desktop shortcut now that setup completed successfully.
if ($createShortcut) {
    try {
        # Paths to the source PNG and the generated ICO used by the shortcut.
        $iconPng = Join-Path $root "images\icon.png"
        $iconIco = Join-Path $root "images\icon.ico"
        if (Test-Path $iconPng) {
            # System.Drawing is built into Windows — no extra package needed.
            Add-Type -AssemblyName System.Drawing
            $bmp = [System.Drawing.Bitmap]::new($iconPng)
            # GetHicon() converts the bitmap to a Windows icon handle.
            $ico = [System.Drawing.Icon]::FromHandle($bmp.GetHicon())
            $fs  = [System.IO.File]::Create($iconIco)
            $ico.Save($fs); $fs.Close()
            $ico.Dispose(); $bmp.Dispose()
        }
        # Prefer PowerShell 7 (pwsh); fall back to Windows PowerShell 5 if not installed.
        $ps = if (Get-Command pwsh -ErrorAction SilentlyContinue) { (Get-Command pwsh).Source } else { (Get-Command powershell).Source }
        # Use the WScript.Shell COM object — the standard way to create .lnk shortcuts on Windows.
        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutFile)
        # Configure the shortcut to launch this script via PowerShell in a minimized window.
        $shortcut.TargetPath = $ps
        $shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$(Join-Path $root 'run.ps1')`""
        $shortcut.WorkingDirectory = $root
        $shortcut.Description = "Launch AI Notepad"
        # 0 = hidden window: no console visible at all.
        $shortcut.WindowStyle = 0
        # Apply the custom icon if the PNG-to-ICO conversion succeeded above.
        if (Test-Path $iconIco) { $shortcut.IconLocation = $iconIco }
        # Write the .lnk file to the desktop.
        $shortcut.Save()
        Write-Host "Desktop shortcut created."
    } catch {
        Write-Warning "Could not create shortcut: $_"
    }
}

Write-Host "Starting AI Notepad locally..."
& $python (Join-Path $appDir "ui.py")
