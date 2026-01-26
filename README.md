# AI Notepad

Local Tk desktop notepad with spelling/grammar help via Ollama. The GUI now runs natively on Windows; Docker is only used for the Ollama model server and the shared SQLite vocab under `./data/`.

## Prereqs
- Docker Desktop
- Python 3 + pip on the host (everything else installs into `.venv`)

## Run on Windows (native GUI)
```
powershell -ExecutionPolicy Bypass -File .\run.ps1
```
- Starts the Ollama container (pulls the model if missing), creates/uses `.venv`, seeds `.\data\ainotepad_vocab.db` if needed, then opens the Tk window.
- DB and Ollama stay in Docker; GUI is a normal Windows window.

## Cleanup / rollback
```
powershell -ExecutionPolicy Bypass -File .\cleanup_native.ps1
```
Stops containers and prompts before deleting `.venv` and `.\data`.

## Notes
- Model selection: set `OLLAMA_MODEL` in `.env` (default `gemma3:1b`).
- Data lives in `./data` (bind-mounted for containers and the native app).
- If execution policy blocks scripts, keep using `-ExecutionPolicy Bypass` as shown.
