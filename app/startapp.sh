#!/usr/bin/env sh
set -e

# Seed DB if missing/empty, then run the Tk app. No DB writes after seeding.
DB_FILE="${DB_FILE:-/data/ainotepad_vocab.db}"

echo "Checking SQLite vocab at $DB_FILE..."
python - <<'PY'
import csv
import os
import re
from pathlib import Path
import sqlite3

db_path = os.environ.get("DB_FILE", "/data/ainotepad_vocab.db")
init_dir = Path("/app/initdb")
Path(db_path).parent.mkdir(parents=True, exist_ok=True)

seed_sql = init_dir / "seed_sqlite.sql"

def apply_seed_sql(conn):
    if not seed_sql.exists():
        return False
    sql = seed_sql.read_text(encoding="utf-8")
    # strip transaction wrappers to avoid nested transaction errors
    filtered = []
    for line in sql.splitlines():
        if line.strip().upper() in {"BEGIN;", "COMMIT;", "PRAGMA JOURNAL_MODE=WAL;"}:
            continue
        filtered.append(line)
    conn.executescript("\n".join(filtered))
    conn.commit()
    return True

def load_csv(name, lang):
    path = init_dir / name
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            w = (row[0] or "").strip()
            if not w or w.lower() == "word":
                continue
            out.append((w, lang))
    return out

def seed_from_wordfreq(conn):
    try:
        import wordfreq
    except Exception as e:
        print(f"wordfreq not available: {e}")
        return False

    top_n = int(os.environ.get("WORDLIST_TOP_N", "120000"))
    if top_n <= 0:
        print("WORDLIST_TOP_N=0; skipping wordfreq seed")
        return False
    word_re = re.compile(r"^[A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'\u2019\-]+$")

    freq_by_word = {}
    lang_choice = {}
    for lang in ("en", "fr"):
        try:
            words = wordfreq.top_n_list(lang, top_n)
        except Exception as e:
            print(f"wordfreq failed for {lang}: {e}")
            continue
        for w in words:
            w = (w or "").strip().lower()
            if not w or " " in w:
                continue
            if not word_re.fullmatch(w):
                continue
            freq = int(max(1.0, wordfreq.zipf_frequency(w, lang) * 100))
            prev = freq_by_word.get(w, 0)
            if freq > prev:
                freq_by_word[w] = freq
            prev_lang = lang_choice.get(w)
            if not prev_lang or freq > prev_lang[1]:
                lang_choice[w] = (lang, freq)

    if not freq_by_word:
        print("wordfreq returned no words; falling back to CSVs")
        return False

    cur = conn.cursor()
    words_rows = [(w, f) for w, f in freq_by_word.items()]
    lang_rows = [(w, lang) for w, (lang, _) in lang_choice.items()]

    chunk = 2000
    for i in range(0, len(words_rows), chunk):
        cur.executemany(
            "INSERT INTO words(word,freq) VALUES(?,?) "
            "ON CONFLICT(word) DO UPDATE SET freq = MAX(freq, excluded.freq);",
            words_rows[i:i+chunk],
        )
    for i in range(0, len(lang_rows), chunk):
        cur.executemany(
            "INSERT INTO lang_words(word,lang) VALUES(?,?) "
            "ON CONFLICT(word) DO UPDATE SET lang = excluded.lang;",
            lang_rows[i:i+chunk],
        )
    conn.commit()
    print(f"Seeded {len(words_rows)} words from wordfreq into {db_path}")
    return True

def needs_seed(conn):
    force = os.environ.get("FORCE_RESEED", "0") == "1"
    if force:
        return True
    min_words_raw = os.environ.get("MIN_WORDS_THRESHOLD", "0")
    try:
        min_words = int(min_words_raw)
    except ValueError:
        min_words = 0

    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='words';")
    has_words = cur.fetchone() is not None
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lang_words';")
    has_lang = cur.fetchone() is not None
    if not has_words or not has_lang:
        return True
    try:
        cur.execute("SELECT COUNT(1) FROM words;")
        count = cur.fetchone()[0]
    except Exception:
        return True
    if min_words > 0:
        return count < min_words
    return count == 0

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA journal_mode=WAL;")
cur.fetchone()

if needs_seed(conn):
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS words(
        word TEXT PRIMARY KEY,
        freq INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS bigrams(
        prev TEXT NOT NULL,
        word TEXT NOT NULL,
        freq INTEGER NOT NULL,
        PRIMARY KEY(prev, word)
    );
    CREATE TABLE IF NOT EXISTS lang_words(
        word TEXT PRIMARY KEY,
        lang TEXT NOT NULL
    );
    """)
    conn.commit()

    applied_sql = apply_seed_sql(conn)
    used_wordfreq = seed_from_wordfreq(conn)
    if not used_wordfreq:
        cur.execute("SELECT COUNT(1) FROM words;")
        count = cur.fetchone()[0]
        if count == 0:
            # Fallback seed from CSVs (only if SQL seed not provided)
            words = load_csv("words_en.csv", "en") + load_csv("words_fr.csv", "fr")
            seen = {}
            dedup_words = []
            dedup_lang = []
            for w, lang in words:
                k = w.lower()
                if k in seen:
                    continue
                seen[k] = lang
                dedup_words.append((w,))
                dedup_lang.append((w, lang))

            if dedup_words:
                cur.executemany(
                    "INSERT INTO words(word,freq) VALUES(?,1) "
                    "ON CONFLICT(word) DO UPDATE SET freq = excluded.freq;",
                    dedup_words,
                )
                cur.executemany(
                    "INSERT INTO lang_words(word,lang) VALUES(?,?) "
                    "ON CONFLICT(word) DO UPDATE SET lang = excluded.lang;",
                    dedup_lang,
                )
                conn.commit()
            print(f"Seeded {len(dedup_words)} words into {db_path}")
        elif applied_sql:
            print(f"Applied SQL seed from {seed_sql}")
    else:
        if applied_sql:
            print(f"Applied SQL seed from {seed_sql}")
else:
    print(f"Using existing SQLite vocab at {db_path}")

conn.close()
PY

# Decide how to launch Tk: native display or headless Xvfb fallback
# If user asked for native (HEADLESS=0) but DISPLAY is empty, try a sensible default (:0)
if [ "${HEADLESS:-0}" = "0" ] && [ -z "${DISPLAY:-}" ]; then
  export DISPLAY=:0
  echo "DISPLAY not set; defaulting to :0 for native X display."
fi

RUNNER=""
python - <<'PY'
import sys
try:
    import tkinter as tk
    tk.Tk().destroy()
    sys.exit(0)
except Exception as e:
    print(f"Display test failed: {e}")
    sys.exit(1)
PY
if [ $? -ne 0 ]; then
  echo "Falling back to headless mode (xvfb-run)..."
  RUNNER="xvfb-run -a"
fi

if [ "${HEADLESS:-0}" = "1" ]; then
  echo "HEADLESS=1 set; using Xvfb."
  RUNNER="xvfb-run -a"
fi

echo "Starting AI Notepad..."
if [ "$RUNNER" = "xvfb-run -a" ]; then
  # Avoid inheriting a broken host DISPLAY when using Xvfb
  unset DISPLAY
fi
exec $RUNNER python app.py
