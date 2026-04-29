# AI Notepad

Local Tk desktop notepad with spelling and grammar correction via Ollama. The GUI runs natively on Windows and Linux. Docker is only used for the Ollama LLM server.

## How it works

1. **Type** your text in the editor.
2. After ~0.65 s of inactivity, the LLM checks the current paragraph.
3. A spinning indicator appears while the AI is working.
4. If a correction is found, a **"Correction preview"** popup appears near your cursor — changed words are underlined in the editor.
5. Press **TAB** to apply the correction, or **ESC** to dismiss it.
6. Use **Correct All** (or `Ctrl+Shift+Enter`) to correct the entire document at once — the same popup appears for review before anything is changed.

Word suggestions from the local SQLite vocabulary appear as you type — press **TAB** to accept or **Up/Down** to navigate.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for the Ollama LLM server)
- [Python 3 + pip](https://www.python.org/downloads/) (dependencies install into `.venv`)

### Linux — additional system packages

On Linux `tkinter` is not bundled with Python and must be installed from the system package manager (it cannot be installed via `pip`).

**Debian / Ubuntu:**
```bash
sudo apt-get install python3-tk
```

**Fedora / RHEL:**
```bash
sudo dnf install python3-tkinter
```

**Arch:**
```bash
sudo pacman -S tk
```

To uninstall it later:

```bash
# Debian / Ubuntu
sudo apt-get remove python3-tk

# Fedora / RHEL
sudo dnf remove python3-tkinter

# Arch
sudo pacman -R tk
```

## GPU acceleration

Ollama uses GPU acceleration automatically if an NVIDIA GPU and the NVIDIA Container Toolkit are available. On systems without a GPU, the model runs on CPU — no configuration needed.


## Clone my GitHub repo

```bash
git clone https://github.com/PiWebswiss/AI_Notepad.git
cd AI_Notepad
```

## Run on Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## Run on Linux

```bash
chmod +x ./run.sh
./run.sh
```

On **first run**, the script will ask if you want a desktop shortcut. The shortcut is only created after the entire setup completes successfully.

## Model configuration

Set the model in `.env`:

```env
OLLAMA_MODEL=gemma3:4b
```

The model is downloaded automatically on first run. To change the model, edit `.env` and restart the app. The new model name will appear in the status bar.

If `OLLAMA_MODEL` is missing or empty, the app will report an error and corrections will not run.

## Execution policy (Windows only)

If you want to run `.\run.ps1` directly without `-ExecutionPolicy Bypass`, allow scripts once for your user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

To remove that permission later:

```powershell
Set-ExecutionPolicy -Scope CurrentUser Undefined
```

## Cleanup
Cleanup stops the Ollama container, removes downloaded models, the SQLite database, and optionally the Python virtual environment, Docker image, and desktop shortcut.

### Windows

```powershell
.\cleanup.ps1
```

### Linux

```bash
chmod +x ./cleanup.sh
./cleanup.sh
```


