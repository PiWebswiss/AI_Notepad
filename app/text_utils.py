"""Text normalization and post-processing utilities for AI Notepad."""

import re
import unicodedata

# --- Constants ---
# Sentinel string returned by the model when no correction is needed.
NO_CORRECTION_TEXT = "No correction needed"

# Matches lines like "assistant:", "user:", "system:" that indicate chatbot role headers.
_CHATBOT_ROLE_RE = re.compile(r"(?m)^(assistant|user|system)\s*:")


# --- Accent handling ---

def strip_accents(s: str) -> str:
    """Return accent-stripped representation used for fuzzy matching/indexing."""
    # NFD decomposition separates base letters from diacritics; filtering "Mn" removes accents.
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


# --- Text chunking ---

def split_into_chunks(text: str, max_chars: int):
    """Split text into chunks that do not exceed max_chars, keeping blank-line separators."""
    text = text or ""
    if len(text) <= max_chars:
        return [text]

    # Split on blank lines (paragraph boundaries) to keep logical blocks together.
    parts = re.split(r"(\n\s*\n)", text)
    chunks, cur = [], ""

    # Greedily accumulate parts until adding the next one would exceed the limit.
    for part in parts:
        if len(cur) + len(part) <= max_chars:
            cur += part
        else:
            if cur:
                chunks.append(cur)
            cur = part

    if cur:
        chunks.append(cur)

    # If any single chunk is still too large, hard-split it at max_chars boundaries.
    out = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            out.append(chunk)
            continue
        for i in range(0, len(chunk), max_chars):
            out.append(chunk[i : i + max_chars])

    return out


# --- Deduplication ---

def uniq_keep_order(items):
    """Remove duplicates while preserving first-seen order."""
    seen = set()
    out = []
    for item in items:
        if item is None:
            continue
        # Case-insensitive dedup for strings.
        key = item.lower() if isinstance(item, str) else item
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


# --- LLM output cleaning ---

def clean_llm_text(text: str) -> str:
    """Normalize model output and strip common wrapper artifacts."""
    if not text:
        return ""
    # Normalize line endings to Unix-style.
    t = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not t:
        return ""

    # Remove <think>…</think> blocks emitted by reasoning models (e.g. qwen3).
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL).strip()
    # Remove unclosed <think> blocks (model cut off mid-thought).
    t = re.sub(r"<think>.*", "", t, flags=re.DOTALL).strip()
    if not t:
        return ""

    # Strip markdown code fences that some models wrap their output in.
    lines = t.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        t = "\n".join(lines[1:-1]).strip()

    # Remove role prefixes like "assistant:" or "output:".
    t = re.sub(r"^\s*(assistant|response|output)\s*:\s*", "", t, flags=re.IGNORECASE)

    # Remove preamble lines like "Here is the corrected text:".
    t = re.sub(
        r"(?i)^(here[''s]* *(is +)?the +corrected +\w*|corrected +(text|version|paragraph)|correction)[^\n]*\n+",
        "",
        t.strip(),
    ).strip()

    # Strip surrounding quotes if the entire text is wrapped in a matching pair.
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ("'", '"'):
        if t.count(t[0]) == 2:
            t = t[1:-1].strip()

    return t


# --- Correction result checks ---

def is_no_correction(text: str) -> bool:
    """Check for explicit 'no correction' response from the model."""
    t = (text or "").strip().lower()
    return t in (
        NO_CORRECTION_TEXT.lower(),
        "aucune correction necessaire",
        "aucune correction nécessaire",
    )


def looks_like_chatbot_output(text: str) -> bool:
    """Detect generic assistant/meta replies that are invalid as direct edits."""
    t = (text or "").strip()
    if not t:
        return False
    low = t.lower()
    # Check for common AI self-identification phrases.
    if low.startswith(
        (
            "as an ai",
            "as a language model",
            "i am an ai",
            "i'm an ai",
            "i cannot",
            "i can't",
            "i am unable",
            "i'm sorry",
            "sorry",
        )
    ):
        return True
    # Check for "here's the corrected…" preambles.
    if "here's the corrected" in low or "here is the corrected" in low:
        return True
    if "corrected text:" in low or "correction:" in low:
        return True
    # Check for role headers (assistant:, user:, system:).
    if _CHATBOT_ROLE_RE.search(t):
        return True
    return False


# --- Post-correction formatting ---

def post_fix_spacing(text: str) -> str:
    """Apply lightweight punctuation spacing cleanup after correction."""
    if not text:
        return text
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove spaces before punctuation: "word ," → "word,".
    t = re.sub(r"[ \t]+([,.;:!?])", r"\1", t)
    # Remove spaces before closing brackets: "word )" → "word)".
    t = re.sub(r"[ \t]+([\)\]\}])", r"\1", t)
    # Collapse mixed sentence-ending punctuation to '.' (the neutral choice).
    # Covers cases where the model adds '!' or '?' next to the user's '.'.
    # Ellipsis is preserved via the (?<!\.) / (?!\.) guards on both sides.
    t = re.sub(r"(?<!\.)[!?]+\.(?!\.)", ".", t)
    t = re.sub(r"(?<!\.)\.[!?]+(?!\.)", ".", t)
    # Collapse multiple spaces into one.
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t


def post_fix_capitalization(text: str) -> str:
    """Ensure every sentence starts with a capital letter and ends with punctuation."""
    if not text:
        return text
    # After sentence-ending punctuation followed by a space, capitalize the next letter.
    result = re.sub(
        r"([.!?][ \u00a0]+)([a-zà-öø-ÿ])",
        lambda m: m.group(1) + m.group(2).upper(),
        text,
    )
    # Ensure the very first character of the text is uppercase.
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    # Ensure the text ends with sentence-ending punctuation.
    stripped = result.rstrip()
    if stripped and stripped[-1] not in ".!?":
        result = stripped + "."
    return result
