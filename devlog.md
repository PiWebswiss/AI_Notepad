# Dev Log — AI Notepad

Journal of changes made to the project, grouped by theme.

---

## Infrastructure and launch scripts

### Renaming `app.py` to `ui.py`

During the module refactoring, the main file was renamed from `app.py` to `ui.py`. `run.ps1`, `run.sh`, and `requirements.txt` still pointed to the old name, causing a `No such file or directory` error at startup. All references have been updated.

### Removed Dockerfile and unused Docker services

The Tkinter app runs natively on the host (via `run.ps1` or `run.sh`) — only Ollama needs Docker. The `app/Dockerfile` and the `app` and `ollama_init` services in `docker-compose.yml` were never used, so they have been removed. `run.sh` was rewritten to follow the same flow as `run.ps1` (native Python + Ollama in Docker only) — the previous version used X11 and an app container that no longer existed.

### Automatic GPU detection

The hardcoded `deploy.resources.reservations.devices` block in `docker-compose.yml` caused a `could not select device driver "nvidia"` error on any machine without the NVIDIA Container Toolkit (VM, laptop without GPU, CI). Replaced with a `${DOCKER_RUNTIME:-runc}` variable in the `runtime` field, driven by `run.sh` / `run.ps1` which detect `nvidia-smi` + the nvidia Docker runtime at startup. GPU enabled automatically on equipped machines, with a clean CPU fallback elsewhere.

### Docker healthcheck for Ollama

The launch scripts used a loop that retried `ollama list` up to 20 times (1 s between attempts) to wait for the Ollama server to be ready. Replaced with a native Docker healthcheck (pings `ollama list` every 2 s) and a `docker compose up -d --wait ollama` that blocks until the healthcheck passes. The healthcheck initially used `curl`, which was missing from the Ollama image — fixed to use the `ollama list` command, which is guaranteed to be present.

### Pip sentinel moved inside the venv

The `.deps-installed` sentinel file lived at the project root. If the `.venv` was deleted or missing (copied project without venv, rsynced to a Pi), the sentinel would remain → `run.sh` would create an empty venv but skip `pip install` → startup crash with `ModuleNotFoundError`. The sentinel now lives at `$VENV_PATH/.deps-installed`, tying its lifecycle to the venv.

### tkinter check upfront in `run.sh`

If `python3-tk` was missing on Linux, the user would go through the entire pipeline (venv + pip install + seed_db) before hitting an obscure Python traceback. Added a `python3 -c "import tkinter"` check before venv creation, with a clear distro-specific message (apt / dnf / pacman).

### `DB_FILE` and `OLLAMA_HOST` respect the user environment

The scripts were running `export DB_FILE=...` without a fallback, overwriting any value already set by the user. Replaced with `${DB_FILE:-default}` in bash and `if (-not $env:DB_FILE)` in PowerShell.

### More robust `.env` parsing

The `sed` parser in `run.sh` didn't strip surrounding quotes. `OLLAMA_MODEL="gemma3:4B"` literally became `"gemma3:4B"`, including the quotes. Added a sed pass to strip both single and double quotes.

### Desktop shortcut moved to end of script

Desktop shortcut creation was happening at the start of the script. If the installation failed later, the user would end up with a shortcut pointing to a broken app. The question is now asked at the start, but the shortcut is only created at the end, once the installation has fully completed. On Windows, the shortcut launches PowerShell in a hidden window (`-WindowStyle Hidden`) so only the Tkinter app appears.

### Clearer launch messages

The script was showing `Ensuring model...` on every launch, even when the model was already present. Replaced with two distinct messages: `Model already available.` or `Model not found. Downloading...`.

### Legacy cleanup removed

After moving the sentinel inside the venv, the code that deleted the old root-level sentinel was no longer useful. Removed from `cleanup.sh` and `cleanup.ps1`.

---

## UI and cross-platform rendering

### Per-platform font auto-resolution

The `Segoe UI` and `Cascadia Code` fonts were hardcoded in `ui.py`, but they don't exist on Linux. Replaced with 3 constants (`FONT_FAMILY_UI`, `FONT_FAMILY_UI_SEMIBOLD`, `FONT_FAMILY_MONO`) resolved at startup via `tkinter.font.families()` with fallback chains: `Segoe UI → Noto Sans → DejaVu Sans`, `Cascadia Code → Cascadia Mono → DejaVu Sans Mono`.

### Automatic `fonts-cascadia-code` installation on Linux

On Linux, `run.sh` detects whether `fonts-cascadia-code` is missing and offers to install it via `apt-get install`. Best-effort only — silently skipped if `sudo`, `apt-get`, or the package are unavailable. Allows the editor to visually match the Windows version.

### DPI scaling on Linux

Tk defaults to 72 DPI on X11, which makes every widget and font render smaller than on Windows (which picks up the actual system DPI). Added `self.tk.call("tk", "scaling", 1.333)` on non-Windows platforms right after `super().__init__()` to align Linux rendering with the Windows 96 DPI baseline.

### Button borders removed on Linux

`tk.Button` was drawing a visible border and focus ring on Linux (X11) even with `relief="flat"`. Added `borderwidth=0` and `highlightthickness=0` on all three `tk.Button` instances (toolbar, word popup, close button). Manual hover effect via `<Enter>` / `<Leave>` on the toolbar buttons since `activebackground` isn't applied on hover on Linux Tk.

### tkinter system dependency documented

`requirements.txt` now has a header explaining that `tkinter` can't be installed via pip, and giving distro-specific install commands. A "Linux — additional system packages" section was added to the README with install and uninstall commands.

### Larger correction popup

The correction popup was too small to show the full corrected text. Maximum dimensions increased from 720×420 to 900×550 to show more content without scrolling.

### Popup display after copy-paste

The correction popup wasn't appearing after a copy-paste or in some normal cases, even though the red underlines were correctly drawn. Two bugs fixed:

- **Call order in `show_fix_popup()`**: `_reposition_fix_popup()` was called before `deiconify()`. But `_reposition_fix_popup()` checks `winfo_viewable()` first and returns immediately if the popup isn't visible → the popup would become visible without ever being positioned. Fix: call `deiconify()` → `update_idletasks()` → `_reposition_fix_popup()`.
- **Cursor off-screen**: when `bbox("insert")` returned `None` (typically after pasting a long text), the popup was hidden instead of being positioned. The popup is now centered on the text widget as a fallback.

### Loading spinner

Added a rotating animation in the status bar while the AI works on a correction. The animation starts when the request is sent and stops when the response arrives. Implemented with a Tkinter Canvas drawing a rotating arc.

---

## LLM correction

### Correction simplified (stages 2 and 3 removed)

Block correction used three stages: normal prompt, strict prompt (`strong=True`), then line-by-line correction (`_linewise_fix`). In practice, only stage 1 was useful. Stages 2 and 3 were removed, along with the `_linewise_fix()` method, which greatly simplified `request_block_fix()` and `correct_document()`.

### Chunk splitting for long texts

Automatic correction during typing was sending the entire paragraph to the model in a single block. For long pasted texts without blank lines, this could exceed the model's context capacity (4096 tokens). It now uses `split_into_chunks()` to split long blocks into 1600-character pieces, same as the "Correct All" button. Pieces are corrected one by one then reassembled before display. The `MAX_FIX_CHARS` constant (old truncation limit) was removed.

### "Stale" bug fix

Corrections were systematically rejected as "stale" because `doc_version` changed on every keystroke, even when the block text hadn't changed. Paste operations also incremented the counter multiple times. The freshness check now compares the actual block text instead of `doc_version`. If the text hasn't changed since the request, the correction is accepted.

### "Correct All" empty-text guard

Pressing "Correct All" with an empty editor was sending a useless request to the model. Text is now checked before any model call, and the status displays "No text to correct".

### Visible model errors instead of "No correction needed"

When the model failed (Ollama down, timeout, etc.), the app was showing "No correction needed" instead of an error. The code silently caught the exception and returned the original text, which triggered the misleading message. Workers now track whether an exception occurred (`had_error`). If so, the status displays "Model error" instead of the misleading message. `SHOW_MODEL_ERRORS_IN_STATUS` is enabled by default.

### Simplified Ollama options

The old `_predict_limit()` logic with its magic numbers (`+500` for thinking models, `+60` overhead, `/3` ratio, `OLLAMA_NUM_PREDICT_MIN`/`MAX`) was entirely removed. Only `temperature=0.0` is still explicitly passed to Ollama (essential for deterministic corrections). `num_ctx` and `num_predict` are left to the model's Modelfile defaults.

### `keep_alive` to avoid cold starts

Ollama unloads the model after 5 minutes of inactivity by default. Every correction after a pause would pay a 60+ second reload cost. Added `keep_alive="30m"` in `_do_chat()` to keep the model in VRAM between calls.

### Model preheating at startup

At app launch, a background thread sends a dummy request (`"hi"` with `num_predict=1`) to force the model into VRAM. While the user types their first lines, Ollama finishes loading. When the first pause happens, the model is already ready — no more 60-second wait on first use.

### `think=False` fallback for non-thinking models

The `think=False` parameter prevents "thinking" models (like qwen3) from wasting tokens on `<think>...</think>` reasoning blocks. Models that don't support this parameter were silently erroring out. A `try/except TypeError` now handles both cases: thinking models receive `think=False`, others ignore it.

### Stacked punctuation bug fix (`!.` and `.!`)

When the user typed `.` and the LLM added `!` for emphasis, the corrected text would show `!.` or `.!`. Added two regexes in `post_fix_spacing()` that collapse these mixes to `.` (the neutral user punctuation wins over LLM-added emphasis). Ellipsis (`...`, `...!`, `!...`) is preserved via lookahead / lookbehind guards.

### Final period added in `post_fix_capitalization()`

The function already ensured that every sentence starts with a capital letter. It now also ensures the text ends with sentence-ending punctuation (`.`, `!` or `?`), and adds a period if not.

### Performance analysis: Gemma 3 4B on RTX 3050 4 GB

Ollama logs show that `gemma3:4B` (Q4_K_M, ~3.6 GB) doesn't fully fit in the 4 GB of VRAM on a laptop RTX 3050 after Windows overhead. As a result, Ollama splits the model into `1.8 GiB GPU` + `1.8 GiB CPU`, which slows inference (constant VRAM / RAM transfers). The model is still usable, but at reduced speed. For full-GPU speed, use `gemma3:1B` via `.env` (~700 MB, fits entirely in VRAM). On GPUs with ≥ 6 GB of VRAM, 4B runs fully on GPU at its nominal speed.

---

## Vocabulary and SQLite database

### SQLite fallback for words outside the memory cache

At startup, only the top 150 000 most frequent words are loaded into RAM to limit memory footprint. The remaining ~50 000 words in the database (from the `wordfreq` seed) were inaccessible to suggestions. Added a fallback: if the RAM lookup returns no candidates and the fragment is ≥ 3 characters, a SQL query is made against the `words` table; results are added to the RAM cache and re-ranked with the same algorithm (unigram frequency + bigram bonus). Rare words freshly loaded stay in RAM for the session and are saved at close.

---

## Code quality and audit

### Line-by-line audit and fixes

A full audit of all files revealed several issues:

- **Broken `correct_document()`** — was still using `strong=True` and `_linewise_fix()`, which had been removed. Fixed to follow the simplified flow of `request_block_fix()`.
- **Duplicates in `_FR_APOST_PREFIXES`** (`db.py`) — the tuple contained 20 entries instead of 10. Replaced with 10 straight-apostrophe variants + 10 curly-apostrophe variants.
- **Unused constant `ALLOW_UNKNOWN_WORDS`** (`ui.py`) — defined but never used (`db.py` reads it directly from the environment). Removed.
- **Mojibake in comments** (`ui.py`) — corrupted em-dashes in the `ghost_mode` comments. Replaced with `--`.
- **Mojibake in `"Correcting..."`** — corrupted ellipsis character. Replaced with `...`.
- **Duplicate SQL schema** (`ui.py`) — `CREATE TABLE` and `CREATE INDEX` were present in `ui.py` even though `seed_db.py` already creates them. Removed from `ui.py`.

### Corrupted UTF-8 encoding in `ui.py` fixed

The file contained double-encoded Unicode characters (mojibake). The accented character ranges (`À-Ö`, `Ø-ö`, `ø-ÿ`) in the regexes and the typographic quotes in `PUNCT_CHARS` were unreadable by Python. The regexes in `get_prev_word` and `rebuild_vocab`, as well as `PUNCT_CHARS`, were restored. Removed an invisible BOM on line 1 that was causing a `SyntaxError`.

### Ollama compatibility code removed

The project always installs the latest version of the `ollama` library via pip. The compatibility code for older versions (`dict` vs Pydantic, `TypeError` fallback for `timeout`) was useless. Cleaned up in `llm.py` (`get_ollama_client`, `extract_chat_content`) and `ui.py` (`_ensure_model_available`).

### Dead code removed

Two features existed in the code but were disabled by default and never used:

- **Ghost continuation (Copilot-style)** — constants `USE_LLM_NEXT_GHOST`, `NEXT_GHOST_*`, methods `request_next_ghost()`, `ask_next_ghost_plain()`, `_prepare_next_ghost()`, variables `_after_next`, `_ghost_req`. Only the `"word"` ghost mode (suggestion suffix) remains.
- **LLM word suggestions** — constants `USE_LLM_WORD_SUGGESTIONS`, `WORD_DEBOUNCE_MS`, methods `request_word_suggestions()`, `ask_word_suggestions_plain()`, variables `_after_word`, `_word_req`, `word_cache`. `on_ctrl_space()` simplified to just cycle local suggestions.

Word suggestions come exclusively from the local SQLite vocabulary, never from the LLM.

### Explanatory comments added

Comments added across all files for easier understanding and maintenance:

- `run.ps1`, `cleanup.ps1`: variables, desktop shortcut properties, pip sentinel, local artifact paths, Docker image.
- `app/db.py`: constants (`DB_FILE`, `ALLOW_UNKNOWN_WORDS`, `_ACCENT_RE`), stopwords, language cache, per-language scoring and filtering.
- `app/llm.py`: client cache, Pydantic response format.
- `app/text_utils.py`: sections (accent handling, chunking, deduplication, LLM output cleaning, etc.), regex explanations and chatbot-detection heuristics.
- `app/suggestions.py`: inline parameter docs for `rank_local_candidates`, prefix / fuzzy matching phases, final ranking.
- `app/ui.py`: color palette, debounce handles, request IDs, suggestion / correction state, key bindings, popups, hint bar, imports, typing loop, correction guards, system prompt, spinner, status methods.

### Cosmetic cleanup

Removed excessive whitespace used to align `=` signs in PowerShell scripts and `ui.py` (`$root`, `$shell`, `$shortcut.*`, `$reqFile`, `$venvPath`, `$dataPath`).

---

## Documentation

### Pseudo-code rewritten in French

The SVG diagram contained informal descriptions. Rewritten as proper French pseudo-code using standard keywords (DÉBUT, FIN, TANT QUE, SI, ALORS, ATTENDRE, ENVOYER, RECEVOIR, AFFICHER, APPLIQUER). Removed trailing `:` and `+`. Step 7 (correction validation) clarified: it's the application that filters bad outputs, not the model.

### README fixes

- Typo: `dc AI_Notepad` → `cd AI_Notepad`.
- Links added to Docker Desktop and Python installers in the Prerequisites section.
- Linux section with install and uninstall commands for required system packages.

### `.env` comment fix

The comment said `override the default model chosen in app/app.py`. The model is only defined in `.env`; there is no default in the code. Comment corrected.
