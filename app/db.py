"""Database-backed language detection and language-word filtering."""

import os
import re
import sqlite3

# Path to the SQLite vocabulary database (set by run.ps1 via environment).
DB_FILE = os.environ.get("DB_FILE", "/data/ainotepad_vocab.db")
# When True, words not found in any language set are still accepted as candidates.
ALLOW_UNKNOWN_WORDS = os.environ.get("ALLOW_UNKNOWN_WORDS", "0").strip().lower() in ("1", "true", "yes", "on")

# Regex matching French-specific accented characters, used as a language hint.
_ACCENT_RE = re.compile(r"[àâäæçéèêëîïôœùûüÿ]", re.IGNORECASE)

# Common French apostrophe prefixes (e.g. "l'homme", "d'accord").
# Used to boost the French score during language detection.
_FR_APOST_PREFIXES = (
    "l\u2019", "d\u2019", "j\u2019", "t\u2019", "m\u2019",
    "s\u2019", "c\u2019", "n\u2019", "qu\u2019", "jusqu\u2019",
    "l’", "d’", "j’", "t’", "m’",
    "s’", "c’", "n’", "qu’", "jusqu’",
)

# High-frequency French words used to score language likelihood.
_FR_STOPWORDS = {
    "le",
    "la",
    "les",
    "un",
    "une",
    "des",
    "du",
    "de",
    "et",
    "est",
    "que",
    "qui",
    "pour",
    "dans",
    "pas",
    "plus",
    "au",
    "aux",
    "sur",
    "par",
    "ce",
    "ces",
    "se",
    "sa",
    "son",
    "ses",
    "ne",
    "ni",
    "mais",
    "ou",
    "avec",
    "sans",
    "en",
    "a",
    "etre",
    "avoir",
    "je",
    "tu",
    "il",
    "elle",
    "nous",
    "vous",
    "ils",
    "elles",
    "mon",
    "ton",
    "notre",
    "votre",
    "leur",
    "mes",
    "tes",
    "nos",
    "vos",
    "leurs",
    "ceci",
    "cela",
    "c",
    "l",
    "d",
    "j",
    "t",
    "m",
    "s",
    "n",
    "qu",
    "y",
}

# High-frequency English words used to score language likelihood.
_EN_STOPWORDS = {
    "the",
    "and",
    "is",
    "are",
    "to",
    "of",
    "in",
    "that",
    "this",
    "for",
    "with",
    "on",
    "as",
    "at",
    "be",
    "was",
    "were",
    "by",
    "or",
    "not",
    "it",
    "its",
    "from",
    "a",
    "an",
    "i",
    "you",
    "he",
    "she",
    "we",
    "they",
    "them",
    "his",
    "her",
    "our",
    "your",
    "their",
    "but",
    "if",
    "then",
    "so",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "can",
    "could",
    "should",
}

# Module-level cache; populated once on first call to load_lang_sets().
_LANG_SETS_CACHE = None


def load_lang_sets():
    """Load language word sets from normalized DB table words(word, lang)."""
    global _LANG_SETS_CACHE
    if _LANG_SETS_CACHE is not None:
        return _LANG_SETS_CACHE

    lang_sets = {"en": set(), "fr": set()}
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        # Check whether the 'words' table exists before querying.
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='words';")
        has_words = cur.fetchone() is not None
        if has_words:
            # Load every word tagged as English or French into in-memory sets.
            for word, lang in cur.execute("SELECT word, lang FROM words WHERE lang IN ('en','fr');"):
                w = (word or "").strip().lower()
                l = (lang or "").strip().lower()
                if w and l in ("en", "fr"):
                    lang_sets[l].add(w)
        conn.close()
    except Exception:
        # Fall back to empty sets if the database is missing or corrupt.
        lang_sets = {"en": set(), "fr": set()}

    _LANG_SETS_CACHE = lang_sets
    return _LANG_SETS_CACHE


def detect_lang(text: str) -> str:
    """Detect language (fr/en) using DB hits + heuristics."""
    text = text or ""
    # Tokenize: extract sequences of letters (including accented) and apostrophes.
    tokens = re.findall(r"[A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'\u2019]+", text.lower())
    if not tokens:
        return "en"

    en_score = 0
    fr_score = 0

    # Score each token against the DB word sets (+2 per hit).
    lang_sets = load_lang_sets()
    if lang_sets["en"] or lang_sets["fr"]:
        for word in tokens:
            if word in lang_sets["en"]:
                en_score += 2
            if word in lang_sets["fr"]:
                fr_score += 2

    # Bonus for stopwords (+1 each).
    en_score += sum(1 for word in tokens if word in _EN_STOPWORDS)
    fr_score += sum(1 for word in tokens if word in _FR_STOPWORDS)

    # Bonus for French apostrophe patterns like "l'homme", "d'accord" (+2 each).
    for word in tokens:
        if "'" in word or "\u2019" in word:
            for pref in _FR_APOST_PREFIXES:
                if word.startswith(pref):
                    fr_score += 2
                    break

    # Accented characters strongly suggest French (+2 per accent).
    accent_hits = len(_ACCENT_RE.findall(text))
    if accent_hits:
        fr_score += accent_hits * 2

    # Tie-breaking: accents tip toward French, otherwise default to English.
    if fr_score == en_score:
        if accent_hits > 0:
            return "fr"
        return "en"

    return "fr" if fr_score > en_score else "en"


def is_lang_word(word: str, lang: str) -> bool:
    """Filter candidate words by detected language and configuration flags."""
    w = (word or "").strip().lower()
    if not w:
        return False

    lang_sets = load_lang_sets()
    # If no language data is loaded, accept everything.
    if not lang_sets["en"] and not lang_sets["fr"]:
        return True

    # Check membership in each language set.
    in_en = w in lang_sets["en"]
    in_fr = w in lang_sets["fr"]
    # If the word appears in at least one set, accept it only if it matches the detected language.
    if in_en or in_fr:
        return (lang == "en" and in_en) or (lang == "fr" and in_fr)

    # Word is not in any language set — reject unless unknown words are allowed.
    if not ALLOW_UNKNOWN_WORDS:
        return False

    # Heuristic: accented words are likely French; reject them for English context.
    if lang == "fr" and _ACCENT_RE.search(w):
        return True
    if lang == "en" and _ACCENT_RE.search(w):
        return False
    return True
