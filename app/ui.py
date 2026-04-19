# AI notepad
# - Fast LOCAL word suggestions from SQLite vocabulary (popup + grey ghost suffix)
# - LLM used for grammar/spelling correction (auto preview popup, TAB to apply)

# --- DPI AWARE (Windows) ---
# Request per-monitor DPI awareness so the UI is sharp on high-resolution screens.
# Level 2 = per-monitor V2 (Windows 10+); fall back to the older V1 API if unavailable.
import sys
if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# --- Standard library imports ---
import os
import re
import threading      # Background threads for LLM calls (keeps UI responsive).
import time           # Monotonic clock for model availability caching.
import difflib        # SequenceMatcher for diff underlining and quality checks.
import sqlite3        # SQLite connection for loading vocabulary at startup.
from collections import Counter  # Word and bigram frequency counters.
import tkinter as tk
from tkinter import filedialog, messagebox

# --- Local module imports ---
from db import detect_lang, is_lang_word           # Language detection and word filtering.
from llm import extract_chat_content as _extract_chat_content  # Extract text from Ollama response.
from llm import get_ollama_client as _shared_ollama_client     # Cached Ollama client.
from suggestions import rank_local_candidates      # Prefix + fuzzy word ranking.
from text_utils import (
    NO_CORRECTION_TEXT,      # Sentinel: "No correction needed".
    clean_llm_text,          # Strip model artifacts (<think>, code fences, preambles).
    is_no_correction,        # Check if model said "no correction needed".
    looks_like_chatbot_output,  # Detect chatbot-style replies ("As an AI...").
    post_fix_capitalization, # Capitalize sentence starts + ensure trailing period.
    post_fix_spacing,        # Remove spaces before punctuation, collapse whitespace.
    split_into_chunks,       # Split long text into model-friendly chunks.
    strip_accents,           # Remove diacritics for accent-insensitive matching.
    uniq_keep_order,         # Deduplicate while preserving order.
)

# --- File reading guide ---
# - Config section: runtime knobs and defaults (model, debounce, theme).
# - AINotepad class: UI state, suggestion popup, correction popup, LLM calls.
# - SQLite is loaded once at startup into in-memory counters (vocab, bigrams).
# - All LLM calls run in background threads; results are posted back via after().

# --- .env loading ---
# The app reads configuration from a .env file at the project root.
# This avoids depending on python-dotenv or any external package.

def _find_dotenv_path():
    """Return the first existing .env path (cwd or project root)."""
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, ".env")),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None

def _load_dotenv() -> dict:
    """Lightweight .env loader (no dependencies)."""
    path = _find_dotenv_path()
    if not path:
        return {}
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                # Skip comments and empty lines.
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if not key:
                    continue
                # Strip surrounding quotes from the value.
                if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                    val = val[1:-1]
                data[key] = val
    except Exception:
        return {}
    return data

# Load .env once at module import time.
_DOTENV = _load_dotenv()

# Merge .env values into the process environment (only when not already set).
for _k, _v in _DOTENV.items():
    if _k and (os.environ.get(_k) is None or os.environ.get(_k) == ""):
        os.environ[_k] = _v

def env_flag(name: str, default: bool = False) -> bool:
    """Parse common truthy env values (1/true/yes/on)."""
    val = os.environ.get(name)
    if val is None or val == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")

# ================= CONFIG =================
# Choose the default model used for text generation and corrections.
MODEL = os.environ.get("OLLAMA_MODEL", "")
# Use this URL to connect to the Ollama server.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
try:
    # Set the request timeout in seconds.
    OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "180"))
except ValueError:
    # Keep a safe default timeout when the env value is invalid.
    OLLAMA_TIMEOUT = 180.0
try:
    # Define how often model availability is checked.
    MODEL_CHECK_INTERVAL = float(os.environ.get("MODEL_CHECK_INTERVAL", "30"))
except ValueError:
    # Keep a safe default interval when the env value is invalid.
    MODEL_CHECK_INTERVAL = 30.0
# Serialize model calls when enabled.
LLM_SERIAL = env_flag("LLM_SERIAL", True)
# Inference options (num_predict, num_ctx, temperature) are left to Ollama's
# per-model Modelfile defaults. Override via Ollama Modelfile if needed.

# --- Behavior toggles ---
# Enable SQLite vocabulary loading and usage.
USE_SQLITE_VOCAB = env_flag("USE_SQLITE_VOCAB", True)

# --- Debounce times ---
# Delay before requesting block correction after typing.
FIX_DEBOUNCE_MS  = 650

# --- Context sizes ---
# Maximum context size used for prompts.
MAX_CONTEXT_CHARS = 1800
# Chunk size used when splitting long text for correction.
DOC_CHUNK_CHARS = 1600

# --- Vocab learning window ---
# Delay before rebuilding local vocabulary from typed text.
VOCAB_REBUILD_MS = 1200
# Use only the document tail for local vocabulary learning.
VOCAB_WINDOW_CHARS = 25000

# --- Word suggestions ---
# Minimum fragment length before showing suggestions.
MIN_WORD_FRAGMENT = 2
# Maximum items shown in the suggestions popup.
POPUP_MAX_ITEMS = 3
# Prefix length used for fast local candidate lookup.
# Two characters give a good balance: small enough bucket count, large enough to prune candidates fast.
PREFIX_INDEX_LEN = 2
# Run fuzzy matching only when no strong prefix match is found.
FUZZY_ONLY_IF_NO_PREFIX = True
# Enable fuzzy matching for spelling tolerance.
ENABLE_FUZZY = os.environ.get("ENABLE_FUZZY", "0") == "1"


# Insert a space after accepting a suggestion when needed.
AUTO_SPACE_AFTER_ACCEPT = True
PUNCT_CHARS = set(",.;:!?)]}\"'’”")
# Remove space before punctuation when enabled.
NO_SPACE_BEFORE_PUNCT = True

# Fuzzy matching thresholds.
FUZZY_MIN_RATIO = 0.72  # Minimum SequenceMatcher similarity ratio to accept a fuzzy candidate.
FUZZY_MAX_LEN_DIFF = 3

# SQLite
# SQLite database file path.
DB_FILE = os.environ.get("DB_FILE", "/data/ainotepad_vocab.db")
# Maximum words loaded from SQLite into memory.
DB_TOP_WORDS = int(os.environ.get("DB_TOP_WORDS", "150000"))
# Maximum bigrams loaded from SQLite into memory.
DB_TOP_BIGRAMS = int(os.environ.get("DB_TOP_BIGRAMS", "80000"))

# Show model errors in the status bar (default on).
SHOW_MODEL_ERRORS_IN_STATUS = os.environ.get("SHOW_MODEL_ERRORS", "1") == "1"

# ================= THEME (VS CODE DARK-ish) =================
# Color palette inspired by VS Code's dark theme.
BG = "#0b0f14"           # Main editor background.
PANEL = "#0f192e"        # Toolbar and status bar background.
FG = "#e9eef5"           # Default text foreground.
MUTED = "#a3b2c6"        # Dimmed / secondary text (hints, status).
SEL_BG = "#1f3554"       # Text selection highlight.
BORDER = "#22324a"       # Border lines between panels.
GHOST = "#7a8697"        # Ghost (inline suggestion) text color.
BAD_BG = "#2a1620"       # Background for underlined correction spans.
POPUP_BG = "#0f1828"     # Popup body background.
POPUP_HEADER = "#0b1423" # Popup header bar background.
POPUP_BORDER = "#22324a" # Popup border color.
POPUP_SHADOW = "#05080e" # Outer shadow / padding area of popups.

# Font families resolved at startup based on what is actually installed on the
# host. Windows provides Segoe UI and Cascadia Code natively; on Linux, install
# fonts-cascadia-code (apt) for an exact match with the Windows editor font.
# The Segoe UI fallback chain uses Noto Sans / DejaVu Sans as free substitutes.
FONT_FAMILY_UI = "Segoe UI"
FONT_FAMILY_UI_SEMIBOLD = "Segoe UI Semibold"
FONT_FAMILY_MONO = "Cascadia Code"

def _resolve_font_families():
    """Pick the first available family in each fallback chain (requires Tk root)."""
    global FONT_FAMILY_UI, FONT_FAMILY_UI_SEMIBOLD, FONT_FAMILY_MONO, FONT_UI, FONT_EDIT
    import tkinter.font as tkfont
    available = set(tkfont.families())

    def pick(candidates):
        for c in candidates:
            if c in available:
                return c
        return candidates[-1]

    FONT_FAMILY_UI = pick(["Segoe UI", "Noto Sans", "DejaVu Sans", "Liberation Sans"])
    FONT_FAMILY_UI_SEMIBOLD = pick(
        ["Segoe UI Semibold", "Noto Sans", "DejaVu Sans", "Liberation Sans"]
    )
    FONT_FAMILY_MONO = pick(
        ["Cascadia Code", "Cascadia Mono", "DejaVu Sans Mono", "Liberation Mono", "Monospace"]
    )
    # Rebuild the tuple fonts now that the families are known.
    FONT_UI = (FONT_FAMILY_UI_SEMIBOLD, 11)
    FONT_EDIT = (FONT_FAMILY_MONO, 14)

# Font used for toolbar labels and hints. Rebuilt after Tk init by _resolve_font_families().
FONT_UI = (FONT_FAMILY_UI_SEMIBOLD, 11)
# Font used in the main text editor area.
FONT_EDIT = (FONT_FAMILY_MONO, 14)

# ================= UTILITIES =================
# Matches a single "word character": letters (including accented Latin), apostrophes, and hyphens.
WORD_CHAR_RE = re.compile(r"[A-Za-z\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff’’\-]")

def get_ollama_client():
    """Return a shared Ollama client configured from app constants."""
    return _shared_ollama_client(OLLAMA_HOST, OLLAMA_TIMEOUT)

# ================= APP =================
# Declare `AINotepad` as the main object that coordinates related state and methods.
class AINotepad(tk.Tk):
    def __init__(self):
        """Initialize UI, runtime state, and in-memory scoring data."""
        # Runtime model:
        # 1) Keep UI responsive.
        # 2) Do fast local suggestions from vocab/bigrams.
        # 3) Ask LLM asynchronously for richer suggestions/fixes.
        # 4) Ignore stale async results via request id + doc version.
        super().__init__()
        # Tk root exists now; resolve which font families are actually installed.
        _resolve_font_families()
        # Match Windows scaling on Linux: Tk defaults to 72 DPI on X11, which makes
        # every widget and font render smaller than on Windows (where Tk picks up
        # the real system DPI). 1.333 corresponds to 96 DPI, the Windows baseline.
        if not sys.platform.startswith("win"):
            try:
                self.tk.call("tk", "scaling", 1.333)
            except Exception:
                pass
        self.title("AI Notepad")
        # Default window size (width x height).
        self.geometry("1800x1000")
        # Set the minimum allowed size.
        self.minsize(900, 580)
        self.configure(bg=BG)

        # Path to the currently open file (None for unsaved new documents).
        self.filepath = None

        # --- Debounce handles ---
        # Each handle stores a pending `after()` timer ID so it can be cancelled on the next keystroke.
        self._after_fix = None           # Block correction timer.
        self._after_vocab = None         # Vocabulary rebuild timer.
        self._after_model_error = None   # Status bar error display timer.
        self._after_status_reset = None  # Transient status message reset timer.
        self._status_override = False    # True while a transient status message is displayed.
        self._spinner_after = None       # Timer for the loading animation.
        self._spinner_index = 0          # Current frame of the animation.
        # Lock that serialises LLM calls so Ollama is never hit by concurrent requests.
        self._llm_lock = threading.Lock()

        # --- Request ids + doc version to drop stale results ---
        # Each async request gets an incrementing ID. When the callback fires, it compares
        # its ID against the current one; if they differ, the result is discarded.
        self._fix_req = 0      # Latest block correction request ID.
        self.doc_version = 0   # Incremented on every keystroke; callbacks use it to detect edits.
        self._model_available = None   # Cached model availability (True/False/None).
        self._model_checked_at = 0.0   # Timestamp of last model availability check.

        # --- Language ---
        self.lang = "en"  # Detected language of the current text ("en" or "fr").

        # --- Vocab + bigrams ---
        # In-memory word frequency and bigram tables used for local suggestion scoring.
        self.vocab = Counter()          # word -> frequency count.
        self.bigram = Counter()         # (prev_word, next_word) -> co-occurrence count.
        self._last_vocab_tail = ""      # Last text window used for vocab rebuild (avoids redundant work).
        self.vocab_norm = {}            # word -> accent-stripped form (cache).
        self.vocab_by_prefix = {}       # prefix -> set of words sharing that prefix.

        # SQLite persistence (read-only: vocab loaded at startup, no writes at runtime)
        self.db = None
        if USE_SQLITE_VOCAB:
            self._db_open_and_load()
        self._rebuild_vocab_index()

        # --- Word suggestion state ---
        self.word_span = None      # (start_index, end_index, full_word) of the word being completed.
        self.word_frag = ""        # Left fragment typed so far (used to compute ghost suffix).
        self.word_items = []       # Current list of ranked word candidates.
        self.word_idx = 0          # Index of the currently highlighted candidate.
        # --- Fix (correction) state ---
        self.fix_start = None      # Editor index where the corrected block starts.
        self.fix_end = None        # Editor index where the corrected block ends.
        self.fix_original = ""     # Original text snapshot (used to verify nothing changed before apply).
        self.fix_corrected = ""    # Corrected text proposed by the model.
        self.fix_version = -1      # Doc version at the time of the correction request.
        self._correct_all_running = False  # True while a whole-document correction is in progress.

        # Ghost label: shows the suffix of the top word suggestion in grey.
        # "none" = hidden, "word" = showing word suffix.
        self.ghost_mode = "none"

        self._build_ui()
        self._build_spinner()
        self._bind_keys()
        self.text.focus_set()

    # ---------- SQLite ----------
    def _db_open_and_load(self):
        """Open SQLite DB and load vocab and bigrams into memory.
        Schema creation is handled by seed_db.py which runs before the app."""
        try:
            self.db = sqlite3.connect(DB_FILE)
            cur = self.db.cursor()
            cur.execute("PRAGMA foreign_keys=ON;")

            # Load the most frequent words into memory for suggestion scoring.
            cur.execute("SELECT word, freq FROM words ORDER BY freq DESC LIMIT ?;", (DB_TOP_WORDS,))
            self.vocab.update({w: int(f) for (w, f) in cur.fetchall()})

            # Bigrams store integer IDs for space efficiency; join back to string words here.
            cur.execute(
                """
                SELECT pw.word, nw.word, b.freq
                FROM bigrams b
                JOIN words pw ON pw.id = b.prev_id
                JOIN words nw ON nw.id = b.next_id
                ORDER BY b.freq DESC
                LIMIT ?;
                """,
                (DB_TOP_BIGRAMS,),
            )
            self.bigram.update({(a, b): int(f) for (a, b, f) in cur.fetchall()})
        except Exception:
            self.db = None

    def _db_save_learned(self):
        """Persist in-memory vocab and bigrams to SQLite so learning survives restarts.
        Uses MAX() on conflict so existing stable frequencies are never decreased."""
        if not self.db:
            return
        try:
            cur = self.db.cursor()
            # Save words: keep max of existing and current frequency.
            word_rows = [(w, int(f), self.lang) for (w, f) in self.vocab.items() if f > 0]
            cur.executemany(
                """
                INSERT INTO words(word, freq, lang) VALUES(?, ?, ?)
                ON CONFLICT(word) DO UPDATE SET freq = MAX(words.freq, excluded.freq);
                """,
                word_rows,
            )
            # Build word -> id map for bigram foreign keys.
            cur.execute("SELECT word, id FROM words;")
            word_id = {w: i for (w, i) in cur.fetchall()}
            # Save bigrams: skip pairs where either word was not inserted.
            bg_rows = []
            for (a, b), f in self.bigram.items():
                if f <= 0:
                    continue
                ai, bi = word_id.get(a), word_id.get(b)
                if ai is not None and bi is not None:
                    bg_rows.append((ai, bi, int(f)))
            cur.executemany(
                """
                INSERT INTO bigrams(prev_id, next_id, freq) VALUES(?, ?, ?)
                ON CONFLICT(prev_id, next_id) DO UPDATE SET freq = MAX(bigrams.freq, excluded.freq);
                """,
                bg_rows,
            )
            self.db.commit()
        except Exception:
            pass

    # ---------------- UI ----------------
    def _build_ui(self):
        """Build main window, editor, suggestion popup, and fix preview popup."""
        top = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        top.pack(side="top", fill="x")

        left = tk.Frame(top, bg=PANEL)
        left.pack(side="left", padx=10, pady=7)

        tk.Label(left, text="AI Notepad", bg=PANEL, fg=FG, font=(FONT_FAMILY_UI, 18, "bold")).pack(
            side="left", padx=(0, 18)
        )

        def btn(txt, cmd):
            # borderwidth=0 + highlightthickness=0 remove the default button
            # border and focus ring that Tk/X11 draws on Linux despite relief="flat".
            b = tk.Button(
                left, text=txt, command=cmd,
                bg=PANEL, fg=FG,
                activebackground="#14203a", activeforeground=FG,
                relief="flat", borderwidth=0, highlightthickness=0,
                font=(FONT_FAMILY_UI, 12),
                padx=12, pady=6
            )
            # Manual hover effect: Linux Tk does not apply activebackground on hover,
            # only on click, so we toggle bg ourselves for a Windows-like feel.
            b.bind("<Enter>", lambda e, w=b: w.configure(bg="#14203a"))
            b.bind("<Leave>", lambda e, w=b: w.configure(bg=PANEL))
            b.pack(side="left", padx=6)
            return b

        # Toolbar buttons for file operations and manual whole-document correction.
        btn("New", self.new_file)
        btn("Open", self.open_file)
        btn("Save", self.save_file)
        btn("Correct All", self.correct_document)

        # Status bar label (right-aligned): shows model name and detected language.
        self.status = tk.Label(top, text=self._status_base_text(), bg=PANEL, fg=MUTED, font=(FONT_FAMILY_UI, 13))
        self.status.pack(side="right", padx=12)

        # --- Main editor area ---
        wrap = tk.Frame(self, bg=BG)
        wrap.pack(side="top", fill="both", expand=True, padx=14, pady=12)

        # Thin border frame around the text widget.
        border = tk.Frame(wrap, bg=BORDER)
        border.pack(fill="both", expand=True)

        inner = tk.Frame(border, bg=BG, padx=1, pady=1)
        inner.pack(fill="both", expand=True)

        self.text = tk.Text(
            inner,
            wrap="word",
            undo=True,
            bg=BG,
            fg=FG,
            insertbackground=FG,
            selectbackground=SEL_BG,
            selectforeground=FG,
            relief="flat",
            borderwidth=0,
            padx=16,
            pady=14,
            font=FONT_EDIT,
            spacing1=2, spacing2=2, spacing3=2,
        )
        self.text.pack(side="left", fill="both", expand=True)

        # Vertical scrollbar linked to the text widget.
        scroll = tk.Scrollbar(inner, command=self.text.yview)
        scroll.pack(side="right", fill="y")
        self.text.config(yscrollcommand=scroll.set)

        # Tag used to underline text spans where the AI found errors.
        self.text.tag_configure("ai_bad", underline=True, background=BAD_BG)

        # Ghost text (inline)
        self.ghost = tk.Label(self.text, text="", bg=BG, fg=GHOST, font=FONT_EDIT)
        self.ghost.place_forget()

        # --- WORD POPUP (inside text widget) ---
        # Small dropdown that appears under the cursor with ranked word candidates.
        self.word_popup = tk.Frame(self.text, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        self.word_popup.place_forget()
        self.word_btns = []
        for i in range(POPUP_MAX_ITEMS):
            # borderwidth=0 + highlightthickness=0 kill the per-item rectangle
            # that Tk/X11 draws around each button on Linux.
            b = tk.Button(
                self.word_popup, text="",
                command=lambda i=i: self.accept_word(i),
                bg=PANEL, fg=FG,
                activebackground="#14203a", activeforeground=FG,
                relief="flat", borderwidth=0, highlightthickness=0,
                font=(FONT_FAMILY_UI, 11),
                padx=10, pady=4,
                anchor="w"
            )
            b.pack(fill="x")
            self.word_btns.append(b)

        # --- FIX PREVIEW POPUP (attached to app, scrollable) ---
        # Floating window that shows the AI-corrected text for the current block.
        # The user can press TAB to accept or ESC to dismiss.
        self.fix_popup = tk.Toplevel(self)
        self.fix_popup.withdraw()        # Hidden until a correction is ready.
        self.fix_popup.overrideredirect(True)  # No title bar or window decorations.
        self.fix_popup.transient(self)    # Always on top of the main window.
        self.fix_popup.configure(bg=POPUP_SHADOW)
        try:
            self.fix_popup.attributes("-topmost", False)
        except Exception:
            pass
        if sys.platform.startswith("win"):
            try:
                self.fix_popup.wm_attributes("-toolwindow", True)
            except Exception:
                pass

        self.fix_frame = tk.Frame(
            self.fix_popup,
            bg=POPUP_BG,
            highlightthickness=1,
            highlightbackground=POPUP_BORDER,
        )
        self.fix_frame.pack(fill="both", expand=True, padx=6, pady=6)

        header = tk.Frame(self.fix_frame, bg=POPUP_HEADER)
        header.pack(side="top", fill="x")

        tk.Label(
            header,
            text="Correction preview",
            bg=POPUP_HEADER,
            fg=FG,
            font=(FONT_FAMILY_UI_SEMIBOLD, 11),
        ).pack(side="left", padx=(12, 6), pady=(8, 6))

        tk.Label(
            header,
            text="TAB apply  |  ESC close",
            bg=POPUP_HEADER,
            fg=MUTED,
            font=(FONT_FAMILY_UI, 10),
        ).pack(side="left", padx=6, pady=(8, 6))

        tk.Button(
            header,
            text="X",
            command=self.hide_fix_popup,
            bg=POPUP_HEADER,
            fg=MUTED,
            activebackground=POPUP_BG,
            activeforeground=FG,
            relief="flat", borderwidth=0, highlightthickness=0,
            font=(FONT_FAMILY_UI, 10),
            padx=6,
            pady=0,
        ).pack(side="right", padx=(6, 10), pady=(6, 6))

        tk.Frame(self.fix_frame, bg=POPUP_BORDER, height=1).pack(fill="x")

        body = tk.Frame(self.fix_frame, bg=POPUP_BG)
        body.pack(side="top", fill="both", expand=True, padx=12, pady=(10, 12))

        self.fix_view = tk.Text(
            body,
            wrap="word",
            bg=POPUP_BG,
            fg=FG,
            insertbackground=FG,
            relief="flat",
            borderwidth=0,
            font=(FONT_FAMILY_UI, 12),
            padx=8,
            pady=8,
            highlightthickness=0,
        )
        self.fix_view.pack(side="left", fill="both", expand=True)

        self.fix_scroll = tk.Scrollbar(
            body,
            command=self.fix_view.yview,
            bg=POPUP_HEADER,
            troughcolor=POPUP_BG,
            activebackground=POPUP_BORDER,
            relief="flat",
        )
        self.fix_scroll.pack(side="right", fill="y")
        self.fix_view.config(yscrollcommand=self.fix_scroll.set)
        self.fix_view.config(state="disabled")

        # --- Bottom hint bar ---
        # Shows keyboard shortcuts and the current word suggestion selection.
        bottom = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        bottom.pack(side="bottom", fill="x")

        self.hint = tk.Label(
            bottom,
            text="TAB apply fix / accept ghost | Ctrl+Space cycle word | Ctrl+Shift+Enter correct ALL (preview) | ESC close",
            bg=PANEL, fg=MUTED, font=FONT_UI, anchor="w"
        )
        self.hint.pack(side="left", padx=10, pady=6)

    # ---------------- Keys ----------------
    def _bind_keys(self):
        """Wire global and editor shortcuts to their handlers."""
        # Close confirmation before quitting.
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- File shortcuts ---
        self.bind("<Control-n>", lambda e: self.new_file())
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<Control-S>", lambda e: self.save_as())

        # --- AI shortcuts ---
        self.bind("<Control-Shift-Return>", lambda e: self.correct_document())  # Correct whole document.
        self.bind("<Control-space>", lambda e: self.on_ctrl_space())            # Cycle / force word suggestion.

        # --- Editor key bindings ---
        self.text.bind("<KeyPress-Tab>", self.on_tab, add=False)     # TAB: accept fix, word, or ghost.
        self.text.bind("<Escape>", lambda e: self.hide_fix_popup() or self.hide_word_popup() or self.hide_ghost(), add=True)
        self.text.bind("<Up>", self.on_up, add=True)                 # Navigate word popup up.
        self.text.bind("<Down>", self.on_down, add=True)             # Navigate word popup down.

        # Main typing hook: fires on every key release and mouse click.
        self.text.bind("<KeyRelease>", self.on_key_release)
        self.text.bind("<ButtonRelease-1>", self.on_key_release)

        # --- Reposition overlays on resize/scroll ---
        self.bind("<Configure>", lambda e: self.after(0, self._reposition_fix_popup), add=True)
        self.text.bind("<Configure>", lambda e: self.after(0, self._reposition_fix_popup), add=True)
        self.text.bind("<MouseWheel>", lambda e: self.after(0, self._reposition_fix_popup) or self.after(0, self.reposition_word_popup) or self.after(0, self.update_ghost_position), add=True)
        self.text.bind("<Button-4>", lambda e: self.after(0, self._reposition_fix_popup) or self.after(0, self.reposition_word_popup) or self.after(0, self.update_ghost_position), add=True)
        self.text.bind("<Button-5>", lambda e: self.after(0, self._reposition_fix_popup) or self.after(0, self.reposition_word_popup) or self.after(0, self.update_ghost_position), add=True)

        # Hide all overlays when the window loses focus or is minimized.
        self.bind("<FocusOut>", lambda e: self.hide_fix_popup() or self.hide_word_popup() or self.hide_ghost(), add=True)
        self.bind("<Unmap>", lambda e: self.hide_fix_popup() or self.hide_word_popup() or self.hide_ghost(), add=True)

    # ---------------- File ops ----------------
    def confirm_discard_changes(self) -> bool:
        """Ask whether modified content should be saved before destructive actions."""
        if self.text.edit_modified():
            res = messagebox.askyesnocancel("Unsaved changes", "Save changes?")
            if res is None:
                return False
            if res:
                return self.save_file()
        return True

    def new_file(self):
        """Start a new empty document and reset pending AI state."""
        if not self.confirm_discard_changes():
            return
        self.text.delete("1.0", "end")
        self.text.edit_modified(False)
        self.filepath = None
        self.clear_ai()
        self.update_lang()

    def open_file(self):
        """Open a text file into the editor and clear transient AI overlays."""
        if not self.confirm_discard_changes():
            return
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Open error", str(e))
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_modified(False)
        self.filepath = path
        self.clear_ai()
        self.update_lang()

    def save_file(self) -> bool:
        """Save buffer to the current path (or delegate to save_as)."""
        if not self.filepath:
            return self.save_as()
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end-1c"))
            self.text.edit_modified(False)
            return True
        except Exception as e:
            messagebox.showerror("Save error", str(e))
            return False

    def save_as(self) -> bool:
        """Prompt for destination path and save the current document."""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",

            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return False
        self.filepath = path
        return self.save_file()

    def on_close(self):
        """Close window only after unsaved-check and resource cleanup."""
        if self.confirm_discard_changes():
            try:
                self._db_save_learned()
                if self.db:
                    self.db.close()
            except Exception:
                pass
            self.destroy()

    # ---------------- Helpers ----------------
    def _lang_label(self) -> str:
        return "FR" if self.lang == "fr" else "EN"

    def _status_base_text(self) -> str:
        return f"Model: {MODEL} | Lang: {self._lang_label()}"

    def _status_with_lang(self, msg: str) -> str:
        return f"{msg} | Lang: {self._lang_label()}"

    def _clear_status_override(self):
        self._status_override = False
        self.status.config(text=self._status_base_text())

    def _show_transient_status(self, msg: str, ms: int = 2000):
        self._status_override = True
        self.status.config(text=self._status_with_lang(msg))
        if self._after_status_reset:
            self.after_cancel(self._after_status_reset)
        self._after_status_reset = self.after(ms, self._clear_status_override)

    def _build_spinner(self):
        """Create a hidden spinner in the toolbar, between buttons and status."""
        size = 46
        self._spin_size = size
        self._spin_canvas = tk.Canvas(
            self.status.master, width=size, height=size,
            bg=PANEL, highlightthickness=0,
        )
        self._spin_angle = 0

    def _start_spinner(self):
        """Show a spinning arc in the center of the editor."""
        self._spin_angle = 0
        # Show spinner between the buttons and the status label.
        self._spin_canvas.pack(side="right", padx=(12, 12), before=self.status)
        def tick():
            s = self._spin_size
            pad = 4
            self._spin_canvas.delete("all")
            # Draw the arc (270 degrees, leaving a gap).
            self._spin_canvas.create_arc(
                pad, pad, s - pad, s - pad,
                start=self._spin_angle, extent=270,
                style="arc", outline=FG, width=3,
            )
            self._spin_angle = (self._spin_angle + 25) % 360
            self._spinner_after = self.after(40, tick)
        tick()

    def _stop_spinner(self):
        """Hide the spinning wheel and restore normal status text."""
        if self._spinner_after:
            self.after_cancel(self._spinner_after)
            self._spinner_after = None
        self._spin_canvas.pack_forget()
        self.status.config(text=self._status_base_text())

    def _refresh_status_base(self):
        """Restore default status text unless a transient message or error is showing."""
        if self._status_override:
            return
        cur = self.status.cget("text")
        # Don't overwrite progress or error messages.
        if cur.startswith("Correcting"):
            return
        if SHOW_MODEL_ERRORS_IN_STATUS and cur.startswith("LLM error:"):
            return
        self.status.config(text=self._status_base_text())

    def set_status(self, txt: str):
        """Update status bar, optionally hiding runtime error details."""
        if SHOW_MODEL_ERRORS_IN_STATUS:
            self.status.config(text=self._status_with_lang(txt))
        else:
            self.status.config(text=self._status_base_text())

    def _report_model_error(self, err: Exception):
        """Display transient model errors in status bar."""
        if not SHOW_MODEL_ERRORS_IN_STATUS:
            return

        msg = self._status_with_lang(f"LLM error: {err}")

        def ui():
            self.status.config(text=msg)
            if self._after_model_error:
                self.after_cancel(self._after_model_error)
            self._after_model_error = self.after(4500, lambda: self.status.config(text=self._status_base_text()))

        self.after(0, ui)

    def _ensure_model_available(self) -> bool:
        """Check and cache availability of the configured Ollama model.
        Queries Ollama only every MODEL_CHECK_INTERVAL seconds to avoid
        hammering the server on every keystroke."""
        now = time.monotonic()
        # Return cached result if checked recently.
        if self._model_available is True and (now - self._model_checked_at) < MODEL_CHECK_INTERVAL:
            return True
        if not MODEL:
            self._model_available = False
            self._model_checked_at = now
            self._report_model_error(RuntimeError("OLLAMA_MODEL is not set"))
            return False

        try:
            data = get_ollama_client().list()
        except Exception as e:
            self._model_available = False
            self._model_checked_at = now
            self._report_model_error(e)
            return False

        # Extract model names from the Pydantic response object.
        names = set()
        for m in (data.models or []):
            if m.model:
                names.add(m.model)

        if MODEL not in names:
            self._model_available = False
            self._model_checked_at = now
            self._report_model_error(RuntimeError(f"Model not found: {MODEL}"))
            return False

        self._model_available = True
        self._model_checked_at = now
        return True

    def _ollama_chat(self, messages, options):
        """Single call path for Ollama requests with error propagation."""
        try:
            if not self._ensure_model_available():
                raise RuntimeError(f"Model not available: {MODEL}")
            client = get_ollama_client()
            # Serialise LLM calls with a lock so concurrent fix/suggestion requests don't
            # overload the local Ollama server and produce garbled interleaved responses.
            if LLM_SERIAL:
                with self._llm_lock:
                    return self._do_chat(client, messages, options)
            return self._do_chat(client, messages, options)
        except Exception as e:
            self._report_model_error(e)
            raise

    def _do_chat(self, client, messages, options):
        """Call client.chat. Pass think=False for models that support it (e.g. qwen3)
        to avoid wasting tokens on reasoning blocks. Falls back silently for models
        that don't support the parameter (e.g. gemma3).

        keep_alive="30m" keeps the model loaded in VRAM for 30 minutes between calls.
        Without it, Ollama unloads after 5 min of idle, forcing a costly reload on
        the next correction (2-10s perceived latency)."""
        try:
            return client.chat(model=MODEL, messages=messages, options=options,
                               think=False, keep_alive="30m")
        except TypeError:
            return client.chat(model=MODEL, messages=messages, options=options,
                               keep_alive="30m")

    def clear_ai(self):
        """Hide all AI overlays (popups, ghost, underlines) and reset correction state.
        Called on New, Open, and other actions that replace the editor content."""
        self.hide_fix_popup()
        self.hide_word_popup()
        self.hide_ghost()
        self.text.tag_remove("ai_bad", "1.0", "end")
        self.fix_start = self.fix_end = None
        self.fix_original = self.fix_corrected = ""
        self.fix_version = -1

    def update_lang(self):
        """Detect active language from recent text before the caret."""
        before = self.text.get("1.0", "insert")[-900:]
        self.lang = detect_lang(before)
        self._refresh_status_base()

    def get_context(self):
        """Return recent full-document context for prompting."""
        return self.text.get("1.0", "end-1c")[-MAX_CONTEXT_CHARS:]

    def get_prev_word(self):
        """Return token preceding current word fragment for bigram scoring."""
        insert = self.text.index("insert")
        before = self.text.get("1.0", insert)[-240:]
        tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+", before)
        if len(tokens) < 2:
            return ""
        return tokens[-2].lower()

    def get_word_under_cursor(self):
        """Resolve word boundaries at caret and return full word + left fragment."""
        insert = self.text.index("insert")
        line_start = self.text.index("insert linestart")
        line_end = self.text.index("insert lineend")

        # Walk backwards from cursor to find the start of the word.
        start = insert
        while True:
            prev = self.text.index(f"{start}-1c")
            if self.text.compare(prev, "<", line_start):
                break
            ch = self.text.get(prev, start)
            if not ch or not WORD_CHAR_RE.fullmatch(ch):
                break
            start = prev

        # Walk forwards from cursor to find the end of the word.
        end = insert
        while True:
            if self.text.compare(end, ">=", line_end):
                break
            ch = self.text.get(end, f"{end}+1c")
            if not ch or not WORD_CHAR_RE.fullmatch(ch):
                break
            end = self.text.index(f"{end}+1c")

        full = self.text.get(start, end)
        left_frag = self.text.get(start, insert)  # Only the part before the cursor.
        if not full or not any(WORD_CHAR_RE.fullmatch(c) for c in full):
            return None, None, "", ""
        return start, end, full, left_frag

    # ---------------- Ghost ----------------
    def hide_ghost(self):
        """Hide inline ghost suggestion text."""
        self.ghost.config(text="")
        self.ghost.place_forget()
        self.ghost_mode = "none"

    def update_ghost_position(self):
        """Keep ghost label anchored to current cursor location."""
        if not self.ghost.cget("text"):
            return
        bbox = self.text.bbox("insert")
        if not bbox:
            self.ghost.place_forget()
            return
        x, y, w, h = bbox
        self.ghost.place(x=x + 1, y=y - 1)

    def set_ghost(self, text: str, mode: str):
        """Show ghost text (inline word suffix suggestion)."""
        text = text or ""
        if not text.strip():
            self.hide_ghost()
            return
        self.ghost.config(text=text)
        self.ghost_mode = mode
        self.update_ghost_position()

    # ---------------- Auto-space after accept ----------------
    def _auto_space_after_accept(self):
        """Insert a trailing space after accepted word suggestion when safe."""
        if not AUTO_SPACE_AFTER_ACCEPT:
            return
        nxt = self.text.get("insert", "insert+1c")
        if nxt and (nxt.isalnum() or nxt in PUNCT_CHARS):
            return
        if nxt == " ":
            return
        self.text.insert("insert", " ")

    def _maybe_remove_space_before_punct(self, event):
        """Delete pre-punctuation space for cleaner typography."""
        if not NO_SPACE_BEFORE_PUNCT:
            return
        if not event or not getattr(event, "char", ""):
            return
        if event.char not in PUNCT_CHARS:
            return
        punct_i = self.text.index("insert-1c")
        prev = self.text.get(f"{punct_i}-1c", punct_i)
        if prev == " ":
            self.text.delete(f"{punct_i}-1c", punct_i)

    # ---------------- Word popup ----------------
    def hide_word_popup(self):
        """Hide candidate popup and clear navigation state."""
        self.word_popup.place_forget()
        self.word_items = []
        self.word_idx = 0
        self.word_span = None
        self._update_hint()

    def show_word_popup(self, items, word_start, word_end, full_word, frag):
        """Display ranked word candidates and sync ghost suffix preview."""
        items = uniq_keep_order(items)[:POPUP_MAX_ITEMS]
        if not items:
            self.hide_word_popup()
            return

        self.word_items = items
        self.word_idx = 0
        self.word_span = (word_start, word_end, full_word)
        self.word_frag = frag

        for i, b in enumerate(self.word_btns):
            if i < len(items):
                b.config(text=items[i], state="normal")
                b.pack(fill="x")
            else:
                b.config(text="", state="disabled")
                b.pack_forget()

        self.reposition_word_popup()
        self._update_hint()

        best = self.word_items[0] if self.word_items else ""
        if best and best.lower().startswith((frag or "").lower()):
            suf = best[len(frag):]
            if suf:
                self.set_ghost(suf, "word")
            else:
                self.hide_ghost()
        else:
            self.hide_ghost()

    def reposition_word_popup(self):
        """Reposition popup under caret on move/scroll."""
        if not self.word_items:
            return
        bbox = self.text.bbox("insert")
        if not bbox:
            self.hide_word_popup()
            return
        x, y, w, h = bbox
        self.word_popup.place(x=x, y=y + h + 6)

    def accept_word(self, idx=0):
        """Replace current token with selected candidate."""
        if not self.word_items or idx < 0 or idx >= len(self.word_items):
            return
        if not self.word_span:
            return
        start, end, original = self.word_span
        cur = self.text.get(start, end)
        if cur != original:
            s2, e2, full2, frag2 = self.get_word_under_cursor()
            if not s2:
                return
            start, end, original = s2, e2, full2
            self.word_span = (start, end, original)

        chosen = self.word_items[idx]
        self.text.delete(start, end)
        self.text.insert(start, chosen)
        self.text.mark_set("insert", f"{start}+{len(chosen)}c")
        self.hide_word_popup()
        self.hide_ghost()
        self._auto_space_after_accept()
        self.text.focus_set()

    def on_up(self, event):
        """Move suggestion selection up."""
        if not self.word_items:
            return None
        self.word_idx = max(0, self.word_idx - 1)
        self._update_hint()
        best = self.word_items[self.word_idx]
        if best.lower().startswith((self.word_frag or "").lower()):
            suf = best[len(self.word_frag):]
            if suf:
                self.set_ghost(suf, "word")
        return "break"

    def on_down(self, event):
        """Move suggestion selection down."""
        if not self.word_items:
            return None
        self.word_idx = min(len(self.word_items) - 1, self.word_idx + 1)
        self._update_hint()
        best = self.word_items[self.word_idx]
        if best.lower().startswith((self.word_frag or "").lower()):
            suf = best[len(self.word_frag):]
            if suf:
                self.set_ghost(suf, "word")
        return "break"

    def on_ctrl_space(self):
        """Cycle through current word suggestions."""
        if self.word_items:
            self.word_idx = (self.word_idx + 1) % len(self.word_items)
            self._update_hint()

    def _update_hint(self):
        """Refresh footer hint text with current word-candidate selection."""
        base = "TAB apply fix / accept ghost | Ctrl+Space cycle word | Ctrl+Shift+Enter correct ALL (preview) | ESC close"
        if self.word_items:
            parts = []
            for i, w in enumerate(self.word_items):
                parts.append(f"[{w}]" if i == self.word_idx else w)
            base += "   |   Words: " + " / ".join(parts)
        self.hint.config(text=base)

    # ---------------- TAB ----------------
    def on_tab(self, event):
        """Priority accept: fix preview, then word suggestion, then ghost text."""
        if self.fix_popup.winfo_viewable() and self.fix_corrected and self.fix_start and self.fix_end:
            self.apply_fix()
            return "break"

        if self.word_items:
            self.accept_word(self.word_idx)
            return "break"

        ghost_txt = self.ghost.cget("text") or ""
        if ghost_txt.strip():
            mode = self.ghost_mode
            self.text.insert("insert", ghost_txt)
            self.hide_ghost()
            # Auto-space after accepted word suffix.
            if mode == "word":
                self._auto_space_after_accept()
            return "break"

        self.text.insert("insert", "\t")
        return "break"

    # ---------------- Local vocab rebuild (also bigrams) ----------------
    def _index_word(self, word: str):
        """Index one word by normalized prefix for fast lookup."""
        if not word:
            return
        w = word.strip().lower()
        if not w or w in self.vocab_norm:
            return
        wn = strip_accents(w)
        if not wn:
            return
        self.vocab_norm[w] = wn
        key = wn[:PREFIX_INDEX_LEN]
        if not key:
            return
        bucket = self.vocab_by_prefix.get(key)
        if bucket is None:
            self.vocab_by_prefix[key] = {w}
        else:
            bucket.add(w)

    def _rebuild_vocab_index(self):
        """Rebuild prefix buckets from current in-memory vocabulary."""
        self.vocab_norm = {}
        self.vocab_by_prefix = {}
        for w in self.vocab:
            self._index_word(w)

    def schedule_vocab_rebuild(self):
        """Debounce vocabulary rebuild triggered by typing activity."""
        if self._after_vocab:
            self.after_cancel(self._after_vocab)
        self._after_vocab = self.after(VOCAB_REBUILD_MS, self.rebuild_vocab)

    def rebuild_vocab(self):
        """Learn recent words and bigrams from editor tail window."""
        self._after_vocab = None
        text = self.text.get("1.0", "end-1c")
        tail = text[-VOCAB_WINDOW_CHARS:]
        if tail == self._last_vocab_tail:
            return
        self._last_vocab_tail = tail

        words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]{2,}", tail)
        norm = [w.lower() for w in words]

        wc = Counter(norm)

        # Track local word transitions for bigram scoring.
        bg = Counter()
        for a, b in zip(norm[:-1], norm[1:]):
            bg[(a, b)] += 1

        self.vocab.update(wc)
        self.bigram.update(bg)
        for w in wc:
            self._index_word(w)
        # Learned data is persisted to SQLite on app close via _db_save_learned().

    def local_candidates_scored(self, frag: str, prev: str, lang: str):
        """Rank local candidates using prefix, frequency, bigram, and fuzzy score."""
        return rank_local_candidates(
            frag=frag,
            prev=prev,
            lang=lang,
            vocab=self.vocab,
            bigram=self.bigram,
            vocab_norm=self.vocab_norm,
            vocab_by_prefix=self.vocab_by_prefix,
            prefix_index_len=PREFIX_INDEX_LEN,
            enable_fuzzy=ENABLE_FUZZY,
            fuzzy_only_if_no_prefix=FUZZY_ONLY_IF_NO_PREFIX,
            fuzzy_min_ratio=FUZZY_MIN_RATIO,
            fuzzy_max_len_diff=FUZZY_MAX_LEN_DIFF,
            popup_max_items=POPUP_MAX_ITEMS,
            is_lang_word=is_lang_word,
        )

    # ---------------- Typing loop ----------------
    def on_key_release(self, event=None):
        """Main typing loop — fires on every key release and mouse click.
        Updates language detection, shows local suggestions, and schedules
        debounced AI requests (word suggestions, block correction, ghost)."""
        try:
            # Ignore modifier-only key releases (Shift, Ctrl, Alt, CapsLock).
            if event is not None and event.keysym in (
                "Shift_L","Shift_R","Control_L","Control_R","Alt_L","Alt_R","Caps_Lock"
            ):
                return

            self._maybe_remove_space_before_punct(event)

            self.doc_version += 1  # Incremented on every edit; used to detect stale async results.
            self.update_lang()     # Re-detect language from recent text.

            # Schedule vocabulary learning from the editor content.
            self.schedule_vocab_rebuild()

            # Reposition overlays after text changes.
            self.update_ghost_position()
            self.reposition_word_popup()
            self.after(0, self._reposition_fix_popup)

            # Show local word suggestions immediately (no AI call needed).
            s, e, full, frag = self.get_word_under_cursor()
            if s and len(frag) >= MIN_WORD_FRAGMENT:
                prev = self.get_prev_word()
                local = self.local_candidates_scored(frag, prev, self.lang)
                if local:
                    self.show_word_popup(local, s, e, full, frag)
                else:
                    self.hide_word_popup()
            else:
                self.hide_word_popup()

            # Cancel pending debounce timer and restart it; this ensures the correction
            # request is only sent once the user pauses typing for the configured delay.

            # Schedule block correction (only if Correct All is not running).
            if not self._correct_all_running:
                if self._after_fix:
                    self.after_cancel(self._after_fix)
                self._after_fix = self.after(FIX_DEBOUNCE_MS, self.request_block_fix)

        except Exception:
            # Never show user stack traces
            return

    # ---------------- Fix region ----------------
    def get_fix_region(self):
        """Return the current paragraph-like block bounded by blank lines."""
        insert = self.text.index("insert")
        cur_line = int(insert.split(".")[0])
        last_line = int(self.text.index("end-1c").split(".")[0])

        start_line = cur_line
        while start_line > 1:
            prev = self.text.get(f"{start_line-1}.0", f"{start_line-1}.end")
            if prev.strip() == "":
                break
            start_line -= 1

        end_line = cur_line
        while end_line < last_line:
            nxt = self.text.get(f"{end_line+1}.0", f"{end_line+1}.end")
            if nxt.strip() == "":
                break
            end_line += 1

        start = f"{start_line}.0"
        end = f"{end_line}.end"
        block = self.text.get(start, end)
        return start, end, block

    # ---------------- Fix popup positioning ----------------
    def _fix_popup_size(self):
        """Compute popup size from screen dimensions with lower/upper bounds."""
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        pad = 12
        w = min(900, int(sw * 0.6))
        h = min(550, int(sh * 0.45))
        w = max(min(500, sw - pad * 2), w)
        h = max(min(300, sh - pad * 2), h)
        return w, h

    def _clamp_to_screen(self, x, y, w, h, pad=10):
        """Clamp popup coordinates so it always stays inside screen area."""
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(pad, min(x, sw - w - pad))
        y = max(pad, min(y, sh - h - pad))
        return x, y

    def _reposition_fix_popup(self):
        """Position fix popup near caret, with automatic above/below fallback."""
        if not self.fix_popup.winfo_viewable():
            return
        bbox = self.text.bbox("insert")
        if not bbox:
            # Cursor off-screen: centre popup on the text widget instead of hiding.
            x_root = self.text.winfo_rootx() + self.text.winfo_width() // 4
            y_root = self.text.winfo_rooty() + 40
        else:
            x, y, _, h0 = bbox
            x_root = self.text.winfo_rootx() + x
            y_root = self.text.winfo_rooty() + y + h0 + 10

        pw, ph = self._fix_popup_size()
        pad = 12
        if bbox:
            above_y = self.text.winfo_rooty() + y - ph - 10
            sh = self.winfo_screenheight()
            if (y_root + ph + pad) > sh and above_y >= pad:
                y_root = above_y
        x_root, y_root = self._clamp_to_screen(x_root, y_root, pw, ph, pad=pad)
        self.fix_popup.geometry(f"{pw}x{ph}+{x_root}+{y_root}")

    def hide_fix_popup(self):
        """Hide correction preview popup."""
        self.fix_popup.withdraw()

    def show_fix_popup(self, corrected: str):
        """Populate and display correction preview content."""
        corrected = clean_llm_text(corrected)
        if not corrected or looks_like_chatbot_output(corrected):
            self.hide_fix_popup()
            return

        self.fix_view.config(state="normal")
        self.fix_view.delete("1.0", "end")
        self.fix_view.insert("1.0", corrected)
        self.fix_view.config(state="disabled")
        self.fix_view.yview_moveto(0.0)

        self.fix_popup.deiconify()
        self.fix_popup.update_idletasks()
        self._reposition_fix_popup()
        self.fix_popup.lift(self)

    # ---------------- Underline diffs ----------------
    def underline_diffs(self, start_index: str, original: str, corrected: str):
        """Underline changed spans in the editor to highlight where the AI found errors."""
        # Clear previous underlines in the affected range.
        try:
            self.text.tag_remove("ai_bad", start_index, f"{start_index}+{len(original)}c")
        except Exception:
            pass

        # Skip diff computation for very long texts (too slow).
        if len(original) > 6000:
            return

        # Compare original vs corrected and underline every changed span.
        sm = difflib.SequenceMatcher(a=original, b=corrected)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            # For insertions (i1 == i2), highlight one character at the insertion point.
            if i1 == i2:
                pos = max(0, min(i1, len(original) - 1))
                s = f"{start_index}+{pos}c"
                e = f"{start_index}+{pos+1}c"
            else:
                s = f"{start_index}+{i1}c"
                e = f"{start_index}+{i2}c"
            try:
                self.text.tag_add("ai_bad", s, e)
            except Exception:
                pass

    # ---------------- Apply fix ----------------
    def apply_fix(self):
        """Apply accepted fix only if source snapshot still matches editor text.
        Called when user presses TAB on the correction preview popup."""
        if not (self.fix_corrected and self.fix_start and self.fix_end):
            return
        # Reject if the document has changed since the correction was generated.
        if self.fix_version != self.doc_version:
            self.hide_fix_popup()
            self.fix_corrected = ""
            return

        # Double-check the block text hasn't been modified.
        current = self.text.get(self.fix_start, self.fix_end)
        if current != self.fix_original:
            self.hide_fix_popup()
            self.fix_corrected = ""
            return

        # Replace the original text with the corrected version.
        self.text.delete(self.fix_start, self.fix_end)
        self.text.insert(self.fix_start, self.fix_corrected)
        self.text.edit_modified(True)

        # Clean up: remove underlines and hide popup.
        self.text.tag_remove("ai_bad", "1.0", "end")
        self.hide_fix_popup()
        self.fix_corrected = ""

    # ---------------- Corrector quality guards ----------------
    def _is_bad_fix(self, original: str, corrected: str) -> bool:
        """Reject suspicious outputs: empty, chatty, too short, or structure loss."""
        o = (original or "").strip()
        c = (corrected or "").strip()
        # Empty output is always bad.
        if not c:
            return True
        # Detect chatbot-style responses ("As an AI...", "Here is the corrected...").
        if looks_like_chatbot_output(c):
            return True
        # Reject if corrected text is too short compared to original.
        min_len = int(len(o) * 0.6)
        if len(o) < 60:
            min_len = int(len(o) * 0.5)
        if len(c) < max(8, min_len):
            return True
        # Reject outputs that diverge too much from the original (similarity check).
        if o and c:
            ratio = difflib.SequenceMatcher(a=o, b=c).ratio()
            if len(o) >= 80 and ratio < 0.70:
                return True
            if len(o) >= 30 and ratio < 0.60:
                return True
            # Reject if the length difference is too large.
            if abs(len(c) - len(o)) > max(12, int(len(o) * 0.25)):
                return True
        # Reject if too many line breaks were removed (structure loss).
        o_nl = original.count("\n")
        c_nl = corrected.count("\n")
        if o_nl >= 2 and c_nl < int(o_nl * 0.7):
            return True
        return False

    def ask_block_fix_plain(self, block: str, lang: str) -> str:
        """Request block correction with strict 'no rewrite' constraints.
        The system prompt is sent with every call because the model has no memory
        between requests — each call is an independent conversation."""
        # French prompt when text is detected as French.
        if lang == "fr":
            system = (
                "Tu es un correcteur orthographique (pas un chatbot). "
                "Corrections minimales uniquement: orthographe, grammaire, ponctuation, majuscules. "
                "REGLE ABSOLUE: chaque phrase commence par une majuscule. "
                "REGLE ABSOLUE: chaque phrase se termine par un point, point d'exclamation ou point d'interrogation. "
                "Ne reformule pas, ne traduis pas, ne change pas le sens ni le style. "
                "Conserve l'ordre des phrases et le vocabulaire. "
                "Conserve EXACTEMENT les retours a la ligne. "
                "Si le texte est deja correct, reponds exactement: No correction needed. "
                "Reponds uniquement avec le texte corrige, rien d'autre."
            )
        # English prompt when text is detected as English.
        else:
            system = (
                "You are a spell checker (not a chatbot). "
                "Minimal edits only: spelling, grammar, punctuation, capitalization. "
                "ABSOLUTE RULE: every sentence must start with a capital letter. "
                "ABSOLUTE RULE: every sentence must end with . or ! or ?. "
                "Do not paraphrase, translate, or change meaning or tone. "
                "Preserve wording and sentence order. "
                "Preserve line breaks EXACTLY. "
                "If the text is already correct, reply exactly: No correction needed. "
                "Reply ONLY with the corrected text, nothing else."
            )

        # temperature=0.0 forces deterministic output (same input -> same correction),
        # essential for spell/grammar checking. Other inference parameters (num_ctx,
        # num_predict) are left to Ollama's per-model Modelfile defaults.
        resp = self._ollama_chat(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": block}],
            options={"temperature": 0.0},
        )
        # Extract the corrected text; fall back to original if the model returned nothing.
        out = clean_llm_text(_extract_chat_content(resp))
        return out if out else block

    # ---------------- AI: BLOCK fix (auto preview) ----------------
    def request_block_fix(self):
        """Build correction preview for current paragraph block."""
        self._after_fix = None
        # Skip if a whole-document correction is already in progress.
        if self._correct_all_running:
            return
        # If another LLM call is running, retry after a short delay.
        if LLM_SERIAL and self._llm_lock.locked():
            self._after_fix = self.after(300, self.request_block_fix)
            return
        # Skip if the model is not available (not installed, Ollama down, etc.).
        if not self._ensure_model_available():
            self.hide_fix_popup()
            self.fix_corrected = ""
            return

        # Get the paragraph block around the cursor (bounded by blank lines).
        start, end, block = self.get_fix_region()
        if not block or len(block.strip()) < 4:
            self.text.tag_remove("ai_bad", "1.0", "end")
            self.hide_fix_popup()
            self.fix_corrected = ""
            return

        lang = self.lang
        req_id = self._fix_req = self._fix_req + 1
        original_snapshot = block
        self._start_spinner()

        def worker():
            # Split long blocks into chunks so each stays within the model's context.
            chunks = split_into_chunks(original_snapshot, DOC_CHUNK_CHARS)
            out_chunks = []
            had_error = False
            for ch in chunks:
                try:
                    fixed = self.ask_block_fix_plain(ch, lang)
                    fixed = clean_llm_text(fixed)
                    fixed = post_fix_spacing(fixed)
                    fixed = post_fix_capitalization(fixed)
                    # If the model returned garbage, keep the original chunk unchanged.
                    if not fixed.strip() or self._is_bad_fix(ch, fixed):
                        out_chunks.append(ch)
                    else:
                        out_chunks.append(fixed)
                except Exception:
                    had_error = True
                    out_chunks.append(ch)
            corrected = "".join(out_chunks)

            def ui():
                self._stop_spinner()
                # Ignore stale response only if a newer request was made for the same block.
                if req_id != self._fix_req:
                    return
                # Check if the block text has actually changed since the request was made.
                current_block = self.text.get(start, end)
                if current_block != original_snapshot:
                    return

                # If the model failed, show an error instead of misleading "No correction needed".
                if had_error and corrected.strip() == original_snapshot.strip():
                    self.text.tag_remove("ai_bad", "1.0", "end")
                    self.hide_fix_popup()
                    self.fix_corrected = ""
                    self._show_transient_status("Model error", ms=3000)
                    return

                if is_no_correction(corrected) or corrected.strip() == original_snapshot.strip():
                    self.text.tag_remove("ai_bad", "1.0", "end")
                    self.hide_fix_popup()
                    self.fix_corrected = ""
                    self._show_transient_status(NO_CORRECTION_TEXT)
                    return
                if self._is_bad_fix(original_snapshot, corrected):
                    self.text.tag_remove("ai_bad", "1.0", "end")
                    self.hide_fix_popup()
                    self.fix_corrected = ""
                    return

                self.fix_start, self.fix_end = start, end
                self.fix_original = original_snapshot
                self.fix_corrected = corrected
                self.fix_version = self.doc_version

                self.underline_diffs(start, original_snapshot, self.fix_corrected)
                self.show_fix_popup(self.fix_corrected)

            self.after(0, ui)

        threading.Thread(target=worker, daemon=True).start()

    # ---------------- Correct ALL (apply automatically) ----------------
    def correct_document(self):
        """Run whole-document correction in chunks and show one preview result."""
        self.update_lang()
        if self._correct_all_running:
            return

        # Don't send empty documents to the model.
        block = self.text.get("1.0", "end-1c")
        if not block or len(block.strip()) < 4:
            self._show_transient_status("No text to correct")
            return

        if not self._ensure_model_available():
            return
        self._correct_all_running = True
        self._start_spinner()
        if self._after_fix:
            self.after_cancel(self._after_fix)
            self._after_fix = None

        start = "1.0"
        end = "end-1c"

        lang = self.lang
        req_version = self.doc_version
        req_id = self._fix_req = self._fix_req + 1
        original_snapshot = block

        chunks = split_into_chunks(original_snapshot, DOC_CHUNK_CHARS)
        total = len(chunks)
        self.status.config(text=self._status_with_lang(f"Correcting... 0/{total}"))

        def worker():
            try:
                out_chunks = []
                had_error = False
                for i, ch in enumerate(chunks, start=1):
                    if req_id != self._fix_req:
                        return
                    corrected = ch
                    try:
                        corrected = self.ask_block_fix_plain(ch, lang)
                        corrected = clean_llm_text(corrected)
                        corrected = post_fix_spacing(corrected)
                        corrected = post_fix_capitalization(corrected)
                        if not corrected.strip() or self._is_bad_fix(ch, corrected):
                            corrected = ch
                    except Exception:
                        had_error = True
                        corrected = ch

                    out_chunks.append(corrected)

                # Reassemble corrected chunks in original order.
                corrected_all = "".join(out_chunks)

                def ui():
                    self.status.config(text=self._status_base_text())
                    if req_id != self._fix_req or req_version != self.doc_version:
                        return
                    if not corrected_all.strip():
                        return
                    if looks_like_chatbot_output(corrected_all):
                        return
                    if had_error and corrected_all.strip() == original_snapshot.strip():
                        self._show_transient_status("Model error", ms=3000)
                        return
                    if is_no_correction(corrected_all) or corrected_all.strip() == original_snapshot.strip():
                        self._show_transient_status(NO_CORRECTION_TEXT)
                        return

                    # Show preview (same as inline fix)
                    self.hide_ghost()
                    self.hide_word_popup()
                    self.fix_start, self.fix_end = start, end
                    self.fix_original = original_snapshot
                    self.fix_corrected = corrected_all
                    self.fix_version = req_version
                    self.underline_diffs(start, original_snapshot, self.fix_corrected)
                    self.show_fix_popup(self.fix_corrected)

                self.after(0, ui)
            finally:
                def done():
                    self._stop_spinner()
                    self._correct_all_running = False
                self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    AINotepad().mainloop()

