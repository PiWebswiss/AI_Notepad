# AI Notepad

Local Tk desktop notepad with spelling/grammar help via Ollama. The GUI runs natively on Windows; Docker is used for the Ollama model server and the shared SQLite vocabulary in `./data/`.

## Prerequisites
- Docker Desktop
- Python 3 + pip on host (dependencies install into `.venv`)

## Run on Windows (native GUI)
```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## Run on Linux (native GUI)
```bash
chmod +x ./run.sh
./run.sh
```

## Restart after Ctrl + C
If you stop AI Notepad with `Ctrl + C`, run the launcher command again.

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

### Linux
```bash
./run.sh
```

<!-- ## App Documentation
- French: [app_readme_fr.md](app_readme_fr.md)
- English: [app_readme_en.md](app_readme_en.md) -->

## Cleanup
### Windows
```powershell
powershell -ExecutionPolicy Bypass -File .\cleanup_native.ps1
```

### Linux
```bash
chmod +x ./cleanup.sh
./cleanup.sh
```
