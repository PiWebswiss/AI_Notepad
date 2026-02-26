<!-- Heading that structures the documentation into navigable sections. -->
# AI Notepad

<!-- Narrative line describing setup, behavior, or operational guidance. -->
Local Tk desktop notepad with spelling/grammar help via Ollama. The GUI now runs natively on Windows; Docker is only used for the Ollama model server and the shared SQLite vocab under `./data/`.

<!-- Heading that structures the documentation into navigable sections. -->
## Prereqs
<!-- Bullet item highlighting a practical usage note. -->
- Docker Desktop
<!-- Bullet item highlighting a practical usage note. -->
- Python 3 + pip on the host (everything else installs into `.venv`)

<!-- Heading that structures the documentation into navigable sections. -->
## Run on Windows (native GUI)
<!-- Fence that starts or ends an executable command example block. -->
```
<!-- Narrative line describing setup, behavior, or operational guidance. -->
powershell -ExecutionPolicy Bypass -File .\run.ps1
<!-- Fence that starts or ends an executable command example block. -->
```
<!-- Bullet item highlighting a practical usage note. -->
- Starts the Ollama container (pulls the model if missing), creates/uses `.venv`, seeds `.\data\ainotepad_vocab.db` if needed, then opens the Tk window.
<!-- Bullet item highlighting a practical usage note. -->
- DB and Ollama stay in Docker; GUI is a normal Windows window.

<!-- Heading that structures the documentation into navigable sections. -->
## Run on Linux (native GUI)
<!-- Narrative line describing setup, behavior, or operational guidance. -->
Prereqs: Docker, Python 3 + venv.
<!-- Fence that starts or ends an executable command example block. -->
```
<!-- Narrative line describing setup, behavior, or operational guidance. -->
docker compose up -d ollama
<!-- Narrative line describing setup, behavior, or operational guidance. -->
python3 -m venv .venv
<!-- Narrative line describing setup, behavior, or operational guidance. -->
source .venv/bin/activate
<!-- Narrative line describing setup, behavior, or operational guidance. -->
pip install --upgrade pip
<!-- Narrative line describing setup, behavior, or operational guidance. -->
pip install -r app/requirements.txt
<!-- Narrative line describing setup, behavior, or operational guidance. -->
export DB_FILE="$PWD/data/ainotepad_vocab.db"
<!-- Narrative line describing setup, behavior, or operational guidance. -->
export OLLAMA_HOST="http://localhost:11434"
<!-- Narrative line describing setup, behavior, or operational guidance. -->
python app/seed_db.py
<!-- Narrative line describing setup, behavior, or operational guidance. -->
python app/app.py
<!-- Fence that starts or ends an executable command example block. -->
```
<!-- Bullet item highlighting a practical usage note. -->
- Ollama stays in Docker; GUI runs on the host.
<!-- Bullet item highlighting a practical usage note. -->
- Model selection: set `OLLAMA_MODEL` in `.env` (default `gemma3:1b`) before starting.
<!-- Bullet item highlighting a practical usage note. -->
- Data lives in `./data` on the host; containers see it via bind mount.

<!-- Heading that structures the documentation into navigable sections. -->
## Cleanup / rollback
<!-- Fence that starts or ends an executable command example block. -->
```
<!-- Narrative line describing setup, behavior, or operational guidance. -->
powershell -ExecutionPolicy Bypass -File .\cleanup_native.ps1
<!-- Fence that starts or ends an executable command example block. -->
```
<!-- Narrative line describing setup, behavior, or operational guidance. -->
Stops containers, removes Docker volumes (including Ollama data), prompts before deleting `.venv`, and always removes `.\data` (DB). It can optionally remove the Ollama image to reclaim space.

<!-- Heading that structures the documentation into navigable sections. -->
## Notes
<!-- Bullet item highlighting a practical usage note. -->
- Model selection: set `OLLAMA_MODEL` in `.env` (default `gemma3:1b`).
<!-- Bullet item highlighting a practical usage note. -->
- Data lives in `./data` (bind-mounted for containers and the native app).
<!-- Bullet item highlighting a practical usage note. -->
- If execution policy blocks scripts, keep using `-ExecutionPolicy Bypass` as shown.
<!-- Bullet item highlighting a practical usage note. -->
- Disk usage: pulled models live in the Ollama volume and can be several GB (gemma3:1b is ~2–3 GB). Use `cleanup_native.ps1` or `docker compose exec -T ollama ollama rm <model>` to reclaim space.
