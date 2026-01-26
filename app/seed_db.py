"""
Seed the SQLite vocabulary database on container startup.

This keeps the logic in one place instead of embedding a large Python heredoc
inside the shell entrypoint.
"""

from __future__ import annotations

import csv
import os
import re
import sqlite3
from pathlib import Path
from typing import Iterable, Tuple


DB_PATH = Path(os.environ.get("DB_FILE", "/data/ainotepad_vocab.db"))
INIT_DIR = Path("/app/initdb")
SEED_SQL = INIT_DIR / "seed_sqlite.sql"


def apply_seed_sql(conn: sqlite3.Connection) -> bool:
    """Apply SQL seed file, stripping outer transaction statements."""
    if not SEED_SQL.exists():
        return False
    sql = SEED_SQL.read_text(encoding="utf-8")
    filtered = []
    for line in sql.splitlines():
        if line.strip().upper() in {"BEGIN;", "COMMIT;", "PRAGMA JOURNAL_MODE=WAL;"}:
            continue
        filtered.append(line)
    conn.executescript("\n".join(filtered))
    conn.commit()
    return True


def load_csv(name: str, lang: str) -> Iterable[Tuple[str, str]]:
    path = INIT_DIR / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            w = (row[0] or "").strip()
            if not w or w.lower() == "word":
                continue
            yield (w, lang)


def seed_from_wordfreq(conn: sqlite3.Connection) -> bool:
    try:
        import wordfreq  # type: ignore
    except Exception as e:
        print(f"wordfreq not available: {e}")
        return False

    top_n = int(os.environ.get("WORDLIST_TOP_N", "120000"))
    if top_n <= 0:
        print("WORDLIST_TOP_N=0; skipping wordfreq seed")
        return False

    word_re = re.compile(r"^[A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'\u2019\\-]+$")
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
            words_rows[i : i + chunk],
        )
    for i in range(0, len(lang_rows), chunk):
        cur.executemany(
            "INSERT INTO lang_words(word,lang) VALUES(?,?) "
            "ON CONFLICT(word) DO UPDATE SET lang = excluded.lang;",
            lang_rows[i : i + chunk],
        )
    conn.commit()
    print(f"Seeded {len(words_rows)} words from wordfreq into {DB_PATH}")
    return True


def needs_seed(conn: sqlite3.Connection) -> bool:
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


def seed_from_csv(conn: sqlite3.Connection) -> None:
    words = list(load_csv("words_en.csv", "en")) + list(load_csv("words_fr.csv", "fr"))
    seen = {}
    dedup_words = []
    dedup_lang = []
    for w, lang in words:
        key = w.lower()
        if key in seen:
            continue
        seen[key] = lang
        dedup_words.append((w,))
        dedup_lang.append((w, lang))

    if dedup_words:
        cur = conn.cursor()
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
    print(f"Seeded {len(dedup_words)} words into {DB_PATH}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
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
        """
    )
    conn.commit()


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.fetchone()

    if not needs_seed(conn):
        print(f"Using existing SQLite vocab at {DB_PATH}")
        conn.close()
        return

    ensure_schema(conn)
    applied_sql = apply_seed_sql(conn)
    used_wordfreq = seed_from_wordfreq(conn)
    if not used_wordfreq:
        cur.execute("SELECT COUNT(1) FROM words;")
        count = cur.fetchone()[0]
        if count == 0:
            seed_from_csv(conn)
        elif applied_sql:
            print(f"Applied SQL seed from {SEED_SQL}")
    else:
        if applied_sql:
            print(f"Applied SQL seed from {SEED_SQL}")
    conn.close()


if __name__ == "__main__":
    main()
