# AI Notepad

Local Tk desktop notepad with spelling and grammar help via Ollama. The GUI runs natively on Windows.
Docker is used for the Ollama model server and the shared SQLite vocabulary in `./data/`.

## How it works

1. **Type** your text in the editor.
2. After ~0.65 s of inactivity, the LLM checks the current paragraph.
3. If a correction is found, a **"Correction preview"** popup appears near your cursor — changed words are underlined in the editor.
4. Press **TAB** to apply the correction, or **ESC** to dismiss it.
5. Use **Correct All** (or `Ctrl+Shift+Enter`) to correct the entire document at once — the same popup appears for review before anything is changed.

> Example: typing `hello there` → popup shows `Hello there` → press TAB to apply.

## Prerequisites

- Docker Desktop
- Python 3 + pip on host (dependencies install into `.venv`)

## Run on Windows (native GUI)

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
OLLAMA_MODEL=qwen3:0.6b
```

If `OLLAMA_MODEL` is missing or empty, the app will report an error and Ollama calls will not run.

### Tested models

| Model | Works |
|-------|-------|
| `qwen3:0.6b` | ✓ (recommended — smallest, fast) |
| `qwen3:1.7b` | ✓ |
| `gemma3:1b` | ✓ |

> **qwen3 note:** qwen3 models output `<think>…</think>` reasoning blocks before answering. These blocks consume tokens from the generation budget, so `OLLAMA_NUM_PREDICT_MAX` defaults to `1500` (instead of `240`) to ensure qwen3 has enough budget to finish thinking and then emit the corrected text. The app strips `<think>` blocks automatically — no configuration needed.

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
