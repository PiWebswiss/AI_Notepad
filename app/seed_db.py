"""
Seed the SQLite vocabulary database on container startup.

This keeps the logic in one place instead of embedding a large Python heredoc
inside the shell entrypoint.
"""

# Import `__future__` to load a dependency used later in this module.
from __future__ import annotations  # allow future typing features if needed

# Import `os` to access environment variables and filesystem helpers.
import os  # env vars for configuration
# Import `re` to use regular expressions for text parsing and cleanup.
import re  # regex for word validation
# Import `sqlite3` to read vocabulary and bigram data from SQLite.
import sqlite3  # built-in SQLite driver
# Import `pathlib` to load a dependency used later in this module.
from pathlib import Path  # filesystem paths


# Tune runtime behavior related to path.
DB_PATH = Path(os.environ.get("DB_FILE", "/data/ainotepad_vocab.db"))  # SQLite file path (volume-mounted)


# Define `seed_from_wordfreq` so this behavior can be reused from other call sites.
def seed_from_wordfreq(conn: sqlite3.Connection) -> bool:
    # Execute this operation as part of the current workflow stage.
    """Use the wordfreq library to insert high-frequency words with language tags."""
    # Wrap fragile operations so failures can be handled gracefully.
    try:
        # Import `wordfreq` to load a dependency used later in this module.
        import wordfreq  # type: ignore  # optional dependency pulled at runtime
    # Handle runtime errors without crashing the editor session.
    except Exception as e:
        # Execute this operation as part of the current workflow stage.
        print(f"wordfreq not available: {e}")  # surface why seeding is skipped
        # Return `False # fall back to no seeding` to the caller for the next decision.
        return False  # fall back to no seeding

    # How many of the most frequent words to pull from wordfreq (can override via WORDLIST_TOP_N env).
    # Store `top n` for use in subsequent steps of this function.
    top_n = int(os.environ.get("WORDLIST_TOP_N", "200000"))  # default: grab 200k most frequent words
    # Guard this branch so downstream logic runs only when `top n <= 0` is satisfied.
    if top_n <= 0:
        # Store `print(WORDLIST TOP N` for use in subsequent steps of this function.
        print("WORDLIST_TOP_N=0; skipping wordfreq seed")  # explicit opt-out
        # Return `False # nothing to do` to the caller for the next decision.
        return False  # nothing to do

    # Prepare language/context data used for suggestion and correction scoring.
    word_re = re.compile(r"^[A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'\u2019\\-]+$")  # allow letters/accents/'/-
    # Snapshot request/version state to ignore stale asynchronous responses.
    freq_by_word = {}  # word -> frequency score
    # Prepare language/context data used for suggestion and correction scoring.
    lang_choice = {}  # word -> (lang, freq) to remember strongest language

    # Iterate through the sequence to process items one by one.
    for lang in ("en", "fr"):  # seed English and French
        # Wrap fragile operations so failures can be handled gracefully.
        try:
            # Prepare language/context data used for suggestion and correction scoring.
            words = wordfreq.top_n_list(lang, top_n)  # get top-N list
        # Handle runtime errors without crashing the editor session.
        except Exception as e:
            # Execute this operation as part of the current workflow stage.
            print(f"wordfreq failed for {lang}: {e}")  # log per-language issues
            # Skip the rest of this iteration and move to the next item.
            continue  # try next language
        # Iterate through the sequence to process items one by one.
        for w in words:  # iterate each candidate word
            # Store `w` for use in subsequent steps of this function.
            w = (w or "").strip().lower()  # normalize case/whitespace
            # Guard this branch so downstream logic runs only when `not w or in w` is satisfied.
            if not w or " " in w:
                # Skip the rest of this iteration and move to the next item.
                continue  # skip empty or multi-word strings
            # Guard this branch so downstream logic runs only when `not word re.fullmatch(w` is satisfied.
            if not word_re.fullmatch(w):
                # Skip the rest of this iteration and move to the next item.
                continue  # skip tokens with invalid chars
            # Snapshot request/version state to ignore stale asynchronous responses.
            freq = int(max(1.0, wordfreq.zipf_frequency(w, lang) * 100))  # convert Zipf to int score
            # Store `prev` for use in subsequent steps of this function.
            prev = freq_by_word.get(w, 0)  # existing best freq
            # Guard this branch so downstream logic runs only when `freq > prev` is satisfied.
            if freq > prev:
                # Snapshot request/version state to ignore stale asynchronous responses.
                freq_by_word[w] = freq  # keep highest freq seen
            # Prepare language/context data used for suggestion and correction scoring.
            prev_lang = lang_choice.get(w)  # existing language choice
            # Guard this branch so downstream logic runs only when `not prev lang or freq > prev lang[1` is satisfied.
            if not prev_lang or freq > prev_lang[1]:
                # Prepare language/context data used for suggestion and correction scoring.
                lang_choice[w] = (lang, freq)  # prefer language with stronger score

    # Guard this branch so downstream logic runs only when `not freq by word` is satisfied.
    if not freq_by_word:
        # Execute this operation as part of the current workflow stage.
        print("wordfreq returned no words; unable to seed.")  # nothing inserted
        # Return `False # signal failure` to the caller for the next decision.
        return False  # signal failure

    # Prepare filesystem/database handles required by the next operations.
    cur = conn.cursor()  # single cursor for batch inserts
    # Prepare language/context data used for suggestion and correction scoring.
    words_rows = [(w, f) for w, f in freq_by_word.items()]  # rows for words table
    # Prepare language/context data used for suggestion and correction scoring.
    lang_rows = [(w, lang) for w, (lang, _) in lang_choice.items()]  # rows for language table

    # Store `chunk` for use in subsequent steps of this function.
    chunk = 2000  # bulk insert in chunks to avoid oversized executemany payloads
    # Iterate through the sequence to process items one by one.
    for i in range(0, len(words_rows), chunk):
        # Execute this operation as part of the current workflow stage.
        cur.executemany(
            # Execute this operation as part of the current workflow stage.
            "INSERT INTO words(word,freq) VALUES(?,?) "
            # Snapshot request/version state to ignore stale asynchronous responses.
            "ON CONFLICT(word) DO UPDATE SET freq = MAX(freq, excluded.freq);",
            # Execute this operation as part of the current workflow stage.
            words_rows[i : i + chunk],
        # Execute this operation as part of the current workflow stage.
        )
    # Iterate through the sequence to process items one by one.
    for i in range(0, len(lang_rows), chunk):
        # Execute this operation as part of the current workflow stage.
        cur.executemany(
            # Execute this operation as part of the current workflow stage.
            "INSERT INTO lang_words(word,lang) VALUES(?,?) "
            # Prepare language/context data used for suggestion and correction scoring.
            "ON CONFLICT(word) DO UPDATE SET lang = excluded.lang;",
            # Execute this operation as part of the current workflow stage.
            lang_rows[i : i + chunk],
        # Execute this operation as part of the current workflow stage.
        )
    # Execute this operation as part of the current workflow stage.
    conn.commit()  # persist inserts
    # Execute this operation as part of the current workflow stage.
    print(f"Seeded {len(words_rows)} words from wordfreq into {DB_PATH}")  # success log
    # Return `True # indicate seeding happened` to the caller for the next decision.
    return True  # indicate seeding happened


# Define `needs_seed` so this behavior can be reused from other call sites.
def needs_seed(conn: sqlite3.Connection) -> bool:
    # Execute this operation as part of the current workflow stage.
    """Return True if tables are missing or the words table is under threshold."""
    # Store `force` for use in subsequent steps of this function.
    force = os.environ.get("FORCE_RESEED", "0") == "1"  # manual override to force reseeding
    # Guard this branch so downstream logic runs only when `force` is satisfied.
    if force:
        # Return `True` to the caller for the next decision.
        return True

    # Prepare language/context data used for suggestion and correction scoring.
    min_words_raw = os.environ.get("MIN_WORDS_THRESHOLD", "0")  # optional lower bound for table size
    # Wrap fragile operations so failures can be handled gracefully.
    try:
        # Prepare language/context data used for suggestion and correction scoring.
        min_words = int(min_words_raw)  # parse threshold
    # Handle runtime errors without crashing the editor session.
    except ValueError:
        # Prepare language/context data used for suggestion and correction scoring.
        min_words = 0  # fallback if env is invalid

    # Prepare filesystem/database handles required by the next operations.
    cur = conn.cursor()  # cursor for metadata checks
    # Store `execute(SELECT name FROM sqlite master WHERE type` for use in subsequent steps of this function.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='words';")
    # Prepare language/context data used for suggestion and correction scoring.
    has_words = cur.fetchone() is not None  # words table exists?
    # Store `execute(SELECT name FROM sqlite master WHERE type` for use in subsequent steps of this function.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lang_words';")
    # Prepare language/context data used for suggestion and correction scoring.
    has_lang = cur.fetchone() is not None  # lang table exists?
    # Guard this branch so downstream logic runs only when `not has words or not has lang` is satisfied.
    if not has_words or not has_lang:
        # Return `True # need to seed if schema missing` to the caller for the next decision.
        return True  # need to seed if schema missing
    # Wrap fragile operations so failures can be handled gracefully.
    try:
        # Execute this operation as part of the current workflow stage.
        cur.execute("SELECT COUNT(1) FROM words;")
        # Store `count` for use in subsequent steps of this function.
        count = cur.fetchone()[0]  # how many words currently stored
    # Handle runtime errors without crashing the editor session.
    except Exception:
        # Return `True # any query failure => reseed` to the caller for the next decision.
        return True  # any query failure => reseed
    # Guard this branch so downstream logic runs only when `min words > 0` is satisfied.
    if min_words > 0:
        # Return `count < min words # under threshold => seed` to the caller for the next decision.
        return count < min_words  # under threshold => seed
    # Return `count == 0 # seed if empty` to the caller for the next decision.
    return count == 0  # seed if empty


# Define `ensure_schema` so this behavior can be reused from other call sites.
def ensure_schema(conn: sqlite3.Connection) -> None:
    # Prepare filesystem/database handles required by the next operations.
    cur = conn.cursor()  # cursor for DDL
    # Execute this operation as part of the current workflow stage.
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
    # Execute this operation as part of the current workflow stage.
    )
    # Execute this operation as part of the current workflow stage.
    conn.commit()  # persist schema changes


# Define `main` so this behavior can be reused from other call sites.
def main() -> None:
    # Execute this operation as part of the current workflow stage.
    """Orchestrate seeding: skip when data exists; otherwise create schema and seed."""
    # Store `mkdir(parents` for use in subsequent steps of this function.
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # ensure directory exists
    # Prepare filesystem/database handles required by the next operations.
    conn = sqlite3.connect(DB_PATH)  # open/create database file
    # Prepare filesystem/database handles required by the next operations.
    cur = conn.cursor()  # cursor for pragmas
    # Store `execute(PRAGMA journal mode` for use in subsequent steps of this function.
    cur.execute("PRAGMA journal_mode=WAL;")  # enable WAL for concurrency
    # Execute this operation as part of the current workflow stage.
    cur.fetchone()  # materialize pragma result

    # Guard this branch so downstream logic runs only when `not needs seed(conn` is satisfied.
    if not needs_seed(conn):
        # Execute this operation as part of the current workflow stage.
        print(f"Using existing SQLite vocab at {DB_PATH}")
        # Execute this operation as part of the current workflow stage.
        conn.close()  # cleanup connection
        # Return `# nothing else to do` to the caller for the next decision.
        return  # nothing else to do

    # Create tables up front so inserts won't fail.
    # Execute this operation as part of the current workflow stage.
    ensure_schema(conn)  # idempotent DDL

    # Store `seeded` for use in subsequent steps of this function.
    seeded = seed_from_wordfreq(conn)  # attempt seeding
    # Guard this branch so downstream logic runs only when `not seeded` is satisfied.
    if not seeded:
        # Execute this operation as part of the current workflow stage.
        print("Seeding skipped: wordfreq unavailable or returned no data.")  # informative warning
    # Execute this operation as part of the current workflow stage.
    conn.close()  # always close


# Guard this branch so downstream logic runs only when `name == main` is satisfied.
if __name__ == "__main__":
    # Execute this operation as part of the current workflow stage.
    main()  # run when invoked directly

