"""Ranking helpers for local word suggestions."""

import difflib

from text_utils import strip_accents, uniq_keep_order


def rank_local_candidates(
    frag: str,          # The text fragment the user is currently typing.
    prev: str,          # The word immediately before the fragment (for bigram context).
    lang: str,          # Language code used to filter vocabulary (e.g. "fr", "en").
    vocab,              # dict[word, frequency] — unigram frequency table.
    bigram,             # dict[(word1, word2), count] — bigram co-occurrence table.
    vocab_norm,         # dict[word, normalized] — cache of accent-stripped forms.
    vocab_by_prefix,    # dict[prefix, set[word]] — words grouped by their first N characters.
    prefix_index_len: int,      # Length of the prefix key used in vocab_by_prefix.
    enable_fuzzy: bool,         # Whether to include fuzzy (approximate) matches.
    fuzzy_only_if_no_prefix: bool,  # If True, only use fuzzy when no exact prefix match exists.
    fuzzy_min_ratio: float,     # Minimum similarity ratio (0–1) to accept a fuzzy match.
    fuzzy_max_len_diff: int,    # Maximum allowed length difference for fuzzy candidates.
    popup_max_items: int,       # Maximum number of suggestions to return.
    is_lang_word,               # Callable(word, lang) -> bool — checks if a word belongs to the given language.
):
    """Rank candidates using prefix match, frequency, bigram, and optional fuzzy score."""
    # Normalize the fragment; return early if there is nothing to match.
    frag = (frag or "").strip()
    if not frag:
        return []

    frag_l = frag.lower()
    # Strip accents for accent-insensitive comparison.
    frag_n = strip_accents(frag_l)
    if not frag_n:
        return []

    # Look up candidate words that share the same prefix bucket.
    key = frag_n[:prefix_index_len]
    candidates = vocab_by_prefix.get(key, set())

    # --- Exact prefix matching ---
    scored = []
    for word in candidates:
        # Skip words that do not belong to the current language.
        if not is_lang_word(word, lang):
            continue
        # Lazily compute and cache the accent-stripped form.
        word_norm = vocab_norm.get(word)
        if not word_norm:
            word_norm = strip_accents(word)
            vocab_norm[word] = word_norm
        # Keep the word only if its normalized form starts with the typed fragment.
        if word_norm.startswith(frag_n):
            # Base score is the word frequency; bigram context gives a bonus.
            score = float(vocab.get(word, 1))
            if prev:
                score += 8.0 * bigram.get((prev, word), 0)
            scored.append((score, word))

    # --- Fuzzy matching (optional) ---
    # Activated when the fragment is at least 3 characters and settings allow it.
    use_fuzzy = enable_fuzzy and len(frag_n) >= 3 and (not scored or not fuzzy_only_if_no_prefix)
    if use_fuzzy:
        first = frag_n[0]
        for word in candidates:
            word_norm = vocab_norm.get(word)
            # Quick filter: first letter must match to avoid expensive similarity checks.
            if not word_norm or word_norm[0] != first:
                continue
            if not is_lang_word(word, lang):
                continue
            # Skip words whose length is too different from the fragment.
            if abs(len(word_norm) - len(frag_n)) > fuzzy_max_len_diff:
                continue
            # Compute similarity ratio between the fragment and the candidate.
            ratio = difflib.SequenceMatcher(a=frag_n, b=word_norm).ratio()
            if ratio >= fuzzy_min_ratio:
                # Fuzzy score weights similarity heavily, with a small frequency bonus.
                score = 80.0 * ratio + 0.25 * float(vocab.get(word, 1))
                if prev:
                    score += 10.0 * bigram.get((prev, word), 0)
                scored.append((score, word))

    # --- Final ranking and formatting ---
    # Sort by descending score, then shortest word first, then alphabetically.
    scored.sort(key=lambda x: (-x[0], len(x[1]), x[1]))
    # Remove duplicates while preserving the sorted order.
    out = uniq_keep_order([word for _, word in scored])
    # Exclude the exact fragment the user already typed.
    out = [word for word in out if word.lower() != frag_l]
    # Capitalize suggestions if the user started with an uppercase letter.
    if frag and frag[0].isupper():
        out = [word.capitalize() for word in out]
    return out[:popup_max_items]
