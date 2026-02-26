"""
Seed the SQLite vocabulary database.

This version is intentionally minimal for fresh-database workflows.
"""

import os
import re
import sqlite3
from pathlib import Path

import wordfreq


DB_PATH = Path(os.environ.get("DB_FILE", "/data/ainotepad_vocab.db"))
WORD_RE = re.compile(r"^[A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'\u2019\\-]+$")


def create_schema(conn: sqlite3.Connection) -> None:
    """Create normalized tables and indexes when missing."""
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS words(
            id INTEGER PRIMARY KEY,
            word TEXT NOT NULL UNIQUE,
            freq INTEGER NOT NULL DEFAULT 0,
            lang TEXT NOT NULL DEFAULT 'en' CHECK(lang IN ('en','fr'))
        );

        CREATE TABLE IF NOT EXISTS bigrams(
            prev_id INTEGER NOT NULL,
            next_id INTEGER NOT NULL,
            freq INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(prev_id, next_id),
            FOREIGN KEY(prev_id) REFERENCES words(id) ON DELETE CASCADE,
            FOREIGN KEY(next_id) REFERENCES words(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_words_word ON words(word);
        CREATE INDEX IF NOT EXISTS idx_words_lang ON words(lang);
        CREATE INDEX IF NOT EXISTS idx_words_freq ON words(freq DESC);
        CREATE INDEX IF NOT EXISTS idx_words_lang_freq ON words(lang, freq DESC);
        CREATE INDEX IF NOT EXISTS idx_bigrams_prev_id ON bigrams(prev_id);
        CREATE INDEX IF NOT EXISTS idx_bigrams_next_id ON bigrams(next_id);
        CREATE INDEX IF NOT EXISTS idx_bigrams_prev_freq ON bigrams(prev_id, freq DESC);
        CREATE INDEX IF NOT EXISTS idx_bigrams_freq ON bigrams(freq DESC);
        """
    )
    conn.commit()


def needs_seed(conn: sqlite3.Connection) -> bool:
    """Seed only when words table is empty."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(1) FROM words;")
    count = cur.fetchone()[0]
    return count == 0


def seed_from_wordfreq(conn: sqlite3.Connection) -> bool:
    """Insert high-frequency EN/FR words with dominant language."""
    top_n = int(os.environ.get("WORDLIST_TOP_N", "200000"))
    if top_n <= 0:
        print("WORDLIST_TOP_N=0; skipping wordfreq seed")
        return False

    freq_by_word: dict[str, int] = {}
    lang_by_word: dict[str, str] = {}

    for lang in ("en", "fr"):
        try:
            words = wordfreq.top_n_list(lang, top_n)
        except Exception as exc:  # pragma: no cover
            print(f"wordfreq failed for {lang}: {exc}")
            continue

        for raw_word in words:
            word = (raw_word or "").strip().lower()
            if not word or " " in word:
                continue
            if not WORD_RE.fullmatch(word):
                continue

            freq = int(max(1.0, wordfreq.zipf_frequency(word, lang) * 100))
            if freq > freq_by_word.get(word, 0):
                freq_by_word[word] = freq
                lang_by_word[word] = lang

    if not freq_by_word:
        print("wordfreq returned no words; unable to seed.")
        return False

    rows = [(w, freq_by_word[w], lang_by_word[w]) for w in freq_by_word]
    cur = conn.cursor()
    chunk = 2000
    for i in range(0, len(rows), chunk):
        cur.executemany(
            """
            INSERT INTO words(word, freq, lang) VALUES(?, ?, ?)
            ON CONFLICT(word) DO UPDATE SET
                freq = MAX(words.freq, excluded.freq),
                lang = excluded.lang;
            """,
            rows[i : i + chunk],
        )

    conn.commit()
    print(f"Seeded {len(rows)} words from wordfreq into {DB_PATH}")
    return True


def main() -> None:
    """Create schema, then seed only if table is empty."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.fetchone()
    cur.execute("PRAGMA foreign_keys=ON;")

    create_schema(conn)

    if not needs_seed(conn):
        print(f"Using existing SQLite vocab at {DB_PATH}")
        conn.close()
        return

    seeded = seed_from_wordfreq(conn)
    if not seeded:
        print("Seeding skipped: wordfreq unavailable or returned no data.")
    conn.close()


if __name__ == "__main__":
    main()
