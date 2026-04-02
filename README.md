# AI Notepad

Local Tk desktop notepad with spelling and grammar help via Ollama. The GUI runs natively on Windows.
Docker is used for the Ollama model server and the shared SQLite vocabulary in `./data/`.

## How it works

1. **Type** your text in the editor.
2. After ~0.65 s of inactivity, the LLM checks the current paragraph.
3. If a correction is found, a **"Correction preview"** popup appears near your cursor — changed words are underlined in the editor.
4. Press **TAB** to apply the correction, or **ESC** to dismiss it.
5. Use **Correct All** (or `Ctrl+Shift+Enter`) to correct the entire document at once — the same popup appears for review before anything is changed.

## Prerequisites

- Docker Desktop
- Python 3 + pip on host (dependencies install into `.venv`)

## Run on Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

On **first run**, the script will ask if you want a desktop shortcut:

```
Create a desktop shortcut for AI Notepad? (y/N)
```

Answer `y` to create an `AI Notepad` icon on your desktop — future launches are a double-click.

## Model configuration

Set the model in one place only: `.env` (single line).

```env
OLLAMA_MODEL=qwen3:1.7b
```

If `OLLAMA_MODEL` is missing or empty, the app will report an error and Ollama calls will not run.

 
If you want to run `.\run.ps1` directly without `-ExecutionPolicy Bypass`, allow scripts once for your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

To remove that permission later (restore the default for your user):

```powershell
Set-ExecutionPolicy -Scope CurrentUser Undefined
```

## Run on Linux (native GUI)

```bash
chmod +x ./run.sh
./run.sh
```

## Cleanup

### Windows

```powershell
.\cleanup.ps1
```

### Linux

```bash
chmod +x ./cleanup.sh
./cleanup.sh
```
