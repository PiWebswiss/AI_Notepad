# AI Notepad

A local, privacy-first text editor with real-time word suggestions and AI-powered grammar correction. No data ever leaves your computer.

---

## How it works

### 1. Word suggestions (SQLite + local scoring)

When you type, the app looks at the characters you have written so far (the *fragment*) and searches a local SQLite database for the most likely completions.

- The database contains up to **200 000 common English and French words**, each with a frequency score built from the `wordfreq` library.
- Words are indexed by their first 2 characters so lookups are instant even with a large dictionary.
- The app also tracks **bigrams** — pairs of words that often appear together (e.g. "good → morning"). When the previous word is known, the top match is boosted by a bigram bonus, so suggestions are contextually relevant.
- Up to 3 candidates appear in a small popup. The best match is also shown as **ghost text** (greyed suffix) directly after the cursor. Press **TAB** or keep typing to accept.

### 2. Grammar and spelling correction (Ollama LLM)

After you pause typing for about 650 ms, the current paragraph is silently sent to a **local language model** (via Ollama) for proofreading.

- Only spelling, grammar, punctuation, and capitalisation are fixed — the model is instructed not to rephrase or change meaning.
- If the model returns a correction, a **preview popup** appears showing the corrected text with the changed parts underlined.
- Press **TAB** to apply the fix, or **ESC** to dismiss it.
- The whole document can also be corrected at once with the **"Correct All"** button (or `Ctrl+Shift+Enter`).
- All processing happens locally through Ollama; no text is sent to any external server.

### 3. Language detection

The app automatically detects whether you are writing in **English or French** based on the words you have typed recently. This controls which dictionary words are offered as suggestions and which language the correction prompt uses.

### 4. Copilot-like continuation (optional)

When `USE_LLM_NEXT_GHOST` is enabled, the app also requests a short 1-3 word continuation from the model after each pause. The suggestion appears as ghost text; press TAB to insert it. This feature is **disabled by default** to keep the UI fast.

---

## Project structure

```
AI_Notepad/
├── app/
│   ├── app.py           Main application: UI, suggestion engine, LLM calls
│   ├── seed_db.py       One-time database seeding from wordfreq
│   ├── requirements.txt Python dependencies (ollama, wordfreq)
│   └── Dockerfile       Container image (used for debug, not the GUI)
├── docker-compose.yml   Defines the Ollama service and optional app container
├── run.ps1              Launch script for Windows (PowerShell)
├── run.sh               Launch script for Linux/macOS (Bash)
├── data/                Persistent SQLite database (created on first run)
└── .venv/               Python virtual environment (created automatically)
```

---

## Database schema

### `words` table

| Column | Type    | Description                            |
|--------|---------|----------------------------------------|
| id     | INTEGER | Auto-increment primary key             |
| word   | TEXT    | Lowercase word (unique)                |
| freq   | INTEGER | Frequency score (higher = more common) |
| lang   | TEXT    | Language: `en` or `fr`                |

### `bigrams` table

| Column  | Type    | Description                                |
|---------|---------|--------------------------------------------|
| prev_id | INTEGER | Foreign key to `words.id` (preceding word) |
| next_id | INTEGER | Foreign key to `words.id` (following word) |
| freq    | INTEGER | How often this word pair appeared together |

> **Why two primary keys on `bigrams`?**
> The table uses a **composite primary key** `(prev_id, next_id)`. A bigram has no meaningful single identifier — it *is* the pair of words. The composite key ensures that each word pair is stored exactly once and prevents duplicates at the database level. This is the standard design for a junction (relationship) table.

---

## Getting started

### Requirements

- **Docker Desktop** (for Ollama and the database container)
- **Python 3.10+** (for the desktop app)
- Internet access on first run only (to download the Ollama model)

### Windows

```powershell
.\run.ps1
```

### Linux / macOS

```bash
bash run.sh
```

Both scripts will:
1. Start the Ollama Docker container
2. Download the default model (`gemma3:1b`) if not already present
3. Create a Python virtual environment and install dependencies
4. Seed the vocabulary database (first run only, takes ~30 s)
5. Launch the AI Notepad desktop window

---

## Keyboard shortcuts

| Key              | Action                                       |
|------------------|----------------------------------------------|
| TAB              | Apply correction preview / accept suggestion |
| Ctrl+Space       | Cycle through word suggestions               |
| Ctrl+Shift+Enter | Correct the entire document (preview)        |
| ESC              | Close popup / dismiss ghost text             |
| Ctrl+S           | Save file                                    |
| Ctrl+Shift+S     | Save As                                      |
| Ctrl+O           | Open file                                    |
| Ctrl+N           | New file                                     |

---

## Configuration

All options can be set as environment variables before launching:

| Variable             | Default                    | Description                                       |
|----------------------|----------------------------|---------------------------------------------------|
| `OLLAMA_MODEL`       | `gemma3:1b`                | Ollama model name to use                          |
| `OLLAMA_HOST`        | `http://localhost:11434`   | Ollama API URL                                    |
| `OLLAMA_TIMEOUT`     | `180`                      | Request timeout in seconds                        |
| `USE_LLM_NEXT_GHOST` | `0`                        | Enable Copilot-like continuation (1 to enable)    |
| `USE_SQLITE_VOCAB`   | `1`                        | Load vocabulary from SQLite (0 to disable)        |
| `WORDLIST_TOP_N`     | `200000`                   | Number of words to seed from wordfreq             |
| `ENABLE_FUZZY`       | `0`                        | Enable fuzzy (typo-tolerant) matching             |
| `DB_TOP_WORDS`       | `150000`                   | Max words loaded into memory at startup           |
| `DB_TOP_BIGRAMS`     | `80000`                    | Max bigrams loaded into memory at startup         |
