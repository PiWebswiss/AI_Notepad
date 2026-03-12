# AI Notepad

Local Tk desktop notepad with spelling and grammar help via Ollama. The GUI runs natively on Windows.
Docker is used for the Ollama model server and the shared SQLite vocabulary in `./data/`.

![alt text](image.png)



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

## Cleanup

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\cleanup.ps1
```

### Linux

```bash
chmod +x ./cleanup.sh
./cleanup.sh
```
