"""
Seed the SQLite vocabulary database on container startup.

This keeps the logic in one place instead of embedding a large Python heredoc
inside the shell entrypoint.
"""

from __future__ import annotations  # allow future typing features if needed

import os  # env vars for configuration
import re  # regex for word validation
import sqlite3  # built-in SQLite driver
from pathlib import Path  # filesystem paths


DB_PATH = Path(os.environ.get("DB_FILE", "/data/ainotepad_vocab.db"))  # SQLite file path (volume-mounted)


def seed_from_wordfreq(conn: sqlite3.Connection) -> bool:
    """Use the wordfreq library to insert high-frequency words with language tags."""
    try:
        import wordfreq  # type: ignore  # optional dependency pulled at runtime
    except Exception as e:
        print(f"wordfreq not available: {e}")  # surface why seeding is skipped
        return False  # fall back to no seeding

    # How many of the most frequent words to pull from wordfreq (can override via WORDLIST_TOP_N env).
    top_n = int(os.environ.get("WORDLIST_TOP_N", "200000"))  # default: grab 200k most frequent words
    if top_n <= 0:
        print("WORDLIST_TOP_N=0; skipping wordfreq seed")  # explicit opt-out
        return False  # nothing to do

    word_re = re.compile(r"^[A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'\u2019\\-]+$")  # allow letters/accents/'/-
    freq_by_word = {}  # word -> frequency score
    lang_choice = {}  # word -> (lang, freq) to remember strongest language

    for lang in ("en", "fr"):  # seed English and French
        try:
            words = wordfreq.top_n_list(lang, top_n)  # get top-N list
        except Exception as e:
            print(f"wordfreq failed for {lang}: {e}")  # log per-language issues
            continue  # try next language
        for w in words:  # iterate each candidate word
            w = (w or "").strip().lower()  # normalize case/whitespace
            if not w or " " in w:
                continue  # skip empty or multi-word strings
            if not word_re.fullmatch(w):
                continue  # skip tokens with invalid chars
            freq = int(max(1.0, wordfreq.zipf_frequency(w, lang) * 100))  # convert Zipf to int score
            prev = freq_by_word.get(w, 0)  # existing best freq
            if freq > prev:
                freq_by_word[w] = freq  # keep highest freq seen
            prev_lang = lang_choice.get(w)  # existing language choice
            if not prev_lang or freq > prev_lang[1]:
                lang_choice[w] = (lang, freq)  # prefer language with stronger score

    if not freq_by_word:
        print("wordfreq returned no words; unable to seed.")  # nothing inserted
        return False  # signal failure

    cur = conn.cursor()  # single cursor for batch inserts
    words_rows = [(w, f) for w, f in freq_by_word.items()]  # rows for words table
    lang_rows = [(w, lang) for w, (lang, _) in lang_choice.items()]  # rows for language table

    chunk = 2000  # bulk insert in chunks to avoid oversized executemany payloads
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
    conn.commit()  # persist inserts
    print(f"Seeded {len(words_rows)} words from wordfreq into {DB_PATH}")  # success log
    return True  # indicate seeding happened


def needs_seed(conn: sqlite3.Connection) -> bool:
    """Return True if tables are missing or the words table is under threshold."""
    force = os.environ.get("FORCE_RESEED", "0") == "1"  # manual override to force reseeding
    if force:
        return True

    min_words_raw = os.environ.get("MIN_WORDS_THRESHOLD", "0")  # optional lower bound for table size
    try:
        min_words = int(min_words_raw)  # parse threshold
    except ValueError:
        min_words = 0  # fallback if env is invalid

    cur = conn.cursor()  # cursor for metadata checks
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='words';")
    has_words = cur.fetchone() is not None  # words table exists?
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lang_words';")
    has_lang = cur.fetchone() is not None  # lang table exists?
    if not has_words or not has_lang:
        return True  # need to seed if schema missing
    try:
        cur.execute("SELECT COUNT(1) FROM words;")
        count = cur.fetchone()[0]  # how many words currently stored
    except Exception:
        return True  # any query failure => reseed
    if min_words > 0:
        return count < min_words  # under threshold => seed
    return count == 0  # seed if empty


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()  # cursor for DDL
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
    conn.commit()  # persist schema changes


def main() -> None:
    """Orchestrate seeding: skip when data exists; otherwise create schema and seed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # ensure directory exists
    conn = sqlite3.connect(DB_PATH)  # open/create database file
    cur = conn.cursor()  # cursor for pragmas
    cur.execute("PRAGMA journal_mode=WAL;")  # enable WAL for concurrency
    cur.fetchone()  # materialize pragma result

    if not needs_seed(conn):
        print(f"Using existing SQLite vocab at {DB_PATH}")
        conn.close()  # cleanup connection
        return  # nothing else to do

    # Create tables up front so inserts won't fail.
    ensure_schema(conn)  # idempotent DDL

    seeded = seed_from_wordfreq(conn)  # attempt seeding
    if not seeded:
        print("Seeding skipped: wordfreq unavailable or returned no data.")  # informative warning
    conn.close()  # always close


if __name__ == "__main__":
    main()  # run when invoked directly

