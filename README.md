# AI Notepad (Dockerized)

Local Tk desktop notepad with spelling/grammar help via Ollama. Word suggestions use a SQLite vocabulary seeded at first start (EN/FR). Stack runs entirely locally: Tk app container + Ollama container.

## Files and what they do
- `docker-compose.yml` — Base stack: `ollama` (LLM), `ollama_init` (one-shot model pull), and `app` (Tk client).
- `docker-compose.x11.yml` — Linux X11 overlay (Xauthority + /tmp/.X11-unix mount).
- `.env` — Compose env (e.g., `OLLAMA_MODEL`, display vars).
- `run.sh` — Linux/WSL launcher; sets up Xauthority and runs with the X11 overlay.
- `run.ps1` — Windows launcher (PowerShell).
- `app/Dockerfile` — Builds the Tk app image (Python + Tk + Xvfb).
- `app/requirements.txt` — Python deps (ollama client).
- `app/app.py` — Tk UI + Ollama integration; reads autocomplete from SQLite.
- `app/startapp.sh` — In-container entrypoint: seeds SQLite once, then launches `app.py` (headless via Xvfb if needed).
- `app/initdb/seed_sqlite.sql` — Optional SQL seed applied on first boot if present.
- `app/initdb/words_en.csv`, `app/initdb/words_fr.csv` — Fallback seed lists (header `word`, one per line) used only when no DB exists.
- `correcteur_v5.py` — Standalone (non-Docker) version of the Tk app; now also loads the CSV wordlists and persists autocomplete in `~/.ai_notepad_autocomplete.db`.
- `app/initdb/` (other) — No extra scripts remain; unused seed helpers were removed.

## Prereqs
- Docker + Docker Compose
- **Display options**
  - **Headless:** set `HEADLESS=1` (edit `.env` or export env var), app runs under Xvfb inside the container.
  - **Native host display:** run an X server and set `DISPLAY` (e.g., `host.docker.internal:0.0` on Windows).
- **Offline runtime:** after the initial model pull, the app only talks to the local Ollama container.
  - If the model is missing, the UI will show an error instead of attempting to download.

## Run (Linux/WSL native display with secure X11)
```
chmod +x run.sh
./run.sh
```
- Linux/WSL: ensure X is running; `DISPLAY` defaults to `:0`. No `xhost +` needed because we use Xauthority.
- Auto model pull is on by default if the model is missing; disable with `NO_AUTO_PULL=1`.

## Run (Windows)
```
.\run.ps1
```
- GUI: start an X server (e.g., VcXsrv), disable access control, and set `DISPLAY=host.docker.internal:0.0` if needed.
- Headless: set `HEADLESS=1`.
- Auto model pull is on by default if the model is missing; disable with `$env:NO_AUTO_PULL="1"`.

By default this starts Ollama and the Tk app (GUI when a display is available). If the model is missing, the launcher runs the one-shot `ollama_init` to pull it once (disable with `NO_AUTO_PULL=1`). SQLite DB lives in the named volume `app_data`; remove that volume to reseed. Follow logs if needed: `docker compose logs -f app`.

## Seeding vocab
- Preferred: place bulk data in `app/initdb/seed_sqlite.sql` (runs once on first boot).
- Otherwise, the container seeds from `wordfreq` (default top 120k per language). Set `WORDLIST_TOP_N` to tune; set to `0` to disable.
- Fallback: `app/initdb/words_en.csv` and `words_fr.csv` (header `word`, one per line). These apply only when the DB does not exist.
- After first seed, the app runs read-only against the DB (both in Docker and in `correcteur_v5.py`’s local DB).
- To force reseed, either delete the `app_data` volume or set `FORCE_RESEED=1` for a single run.
- Word suggestions are prefix-only by default; set `ENABLE_FUZZY=1` to allow fuzzy matches.

## Env overrides (optional)
- `WORDLIST_TOP_N` (default `120000`) — size of local word list per language.
- `FORCE_RESEED=1` — rebuild the vocab DB on next start.
- `MIN_WORDS_THRESHOLD` — auto-reseed if DB has fewer words than this.
- `ENABLE_FUZZY=1` — allow fuzzy word suggestions (less strict).
- `ALLOW_UNKNOWN_WORDS=1` — allow suggestions not present in the dictionary.
- `SHOW_MODEL_ERRORS=1` — show LLM errors in the status bar.
- `USE_LLM_NEXT_GHOST=1` — enable LLM next-word ghost suggestions.
- `USE_SQLITE_VOCAB=0` — disable DB vocab load.
- `NO_AUTO_PULL=1` — disable automatic model pull in `run.sh`/`run.ps1`.
- `OLLAMA_TIMEOUT` (default `180`) — increase if corrections time out.
- `LLM_SERIAL=1` — serialize LLM requests (more stable on slow CPUs).
- `OLLAMA_NUM_PREDICT_MIN`/`OLLAMA_NUM_PREDICT_MAX` — cap output length for fixes.
