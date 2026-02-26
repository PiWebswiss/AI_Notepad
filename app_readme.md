# APP README (FR + EN)

## But / Goal
FR: Ce document explique simplement et en detail comment l'application fonctionne, puis decrit chaque fonction importante.
EN: This document gives a simple but detailed explanation of how the app works, then describes each important function.

## Comment l'app fonctionne (FR)
1. L'application Tkinter demarre, construit l'UI, et initialise les etats internes.
2. Elle charge (optionnellement) le vocabulaire SQLite et cree un index de recherche rapide.
3. A chaque frappe, elle met a jour la langue detectee et le contexte curseur.
4. Elle calcule des suggestions locales (vocab + bigrammes), puis peut interroger le LLM en arriere-plan.
5. Les suggestions apparaissent en popup (mots) et/ou en texte fantome gris (completion).
6. La correction orthographe/grammaire est demandee de facon asynchrone, avec garde-fous qualite.
7. Un popup preview montre les differences; TAB applique la correction si le document n'a pas change.
8. Le mode Correct All corrige par chunks pour eviter les depassements de contexte modele.

### Exemple simple (FR)
- Vous tapez `bonj` -> suggestions locales (`bonjour`) apparaissent.
- Vous pressez TAB -> le mot propose est insere + espace auto si necessaire.
- Vous continuez un paragraphe avec fautes -> popup correction apparait.
- Vous pressez TAB -> la correction preview est appliquee.

## How the app works (EN)
1. The Tkinter app starts, builds the UI, and initializes internal state.
2. It optionally loads SQLite vocabulary and builds a fast lookup index.
3. On each key release, it refreshes detected language and cursor context.
4. It computes local suggestions (vocab + bigrams), then can query the LLM in background.
5. Suggestions appear as popup candidates and/or gray ghost continuation text.
6. Spelling/grammar correction runs asynchronously with quality guards.
7. A preview popup shows diffs; TAB applies only if the document version still matches.
8. Correct All processes text in chunks to stay inside model context limits.

### Simple example (EN)
- You type `bonj` -> local suggestions (`bonjour`) appear.
- You press TAB -> selected word is inserted + auto-space when needed.
- You continue writing with mistakes -> correction preview popup appears.
- You press TAB -> previewed correction is applied.

## Function Reference: `app/app.py`

### Top-level utility functions
| Function | FR (ce que ca fait) | EN (what it does) | Exemple / Example |
|---|---|---|---|
| `env_flag` | Lit une variable d'environnement et retourne un vrai/faux robuste. | Reads an environment variable and returns a robust true/false flag. | `env_flag('USE_SQLITE_VOCAB', True)` |
| `strip_accents` | Supprime les accents pour comparer les mots sans sensibilite aux diacritiques. | Removes accents so word matching is accent-insensitive. | `strip_accents('eleve') -> 'eleve'` |
| `load_lang_sets` | Charge les dictionnaires EN/FR depuis SQLite puis les met en cache. | Loads EN/FR word sets from SQLite and caches them. | `load_lang_sets()` |
| `detect_lang` | Devine la langue active (fr/en) a partir du texte proche du curseur. | Guesses active language (fr/en) from text near the cursor. | `detect_lang('bonjour je vais bien') -> 'fr'` |
| `split_into_chunks` | Decoupe un long texte en blocs pour corriger sans depasser les limites modele. | Splits long text into model-safe chunks for correction. | `split_into_chunks(big_text, 1600)` |
| `get_ollama_client` | Cree/reutilise un client Ollama unique pour toutes les requetes. | Creates/reuses a single Ollama client for all requests. | `client = get_ollama_client()` |
| `uniq_keep_order` | Supprime les doublons sans changer l'ordre des suggestions. | Removes duplicates without changing suggestion order. | `uniq_keep_order(['cat','cat','car'])` |
| `clean_llm_text` | Nettoie la sortie LLM (quotes, code fences, prefixes assistant). | Cleans LLM output (quotes, code fences, assistant prefixes). | `clean_llm_text(raw_response)` |
| `looks_like_chatbot_output` | Bloque les reponses type chatbot qui ne doivent pas aller dans la note. | Filters chatbot-style replies that should not be inserted in notes. | `looks_like_chatbot_output(text)` |
| `post_fix_spacing` | Corrige les espaces autour de la ponctuation apres correction. | Fixes punctuation spacing after correction. | `post_fix_spacing(corrected)` |
| `is_lang_word` | Valide qu'un mot est coherent avec la langue courante. | Validates that a word matches the current language. | `is_lang_word('bonjour', 'fr')` |

### Class `AINotepad` methods
| Method | FR (ce que ca fait) | EN (what it does) | Exemple / Example |
|---|---|---|---|
| `__init__` | Initialise la fenetre, les etats internes, les caches et les widgets. | Initializes window, internal state, caches, and widgets. | `app = AINotepad()` |
| `_db_open_and_load` | Gere la couche SQLite (ou son mode lecture seule) pour vocabulaire/bigrammes. | Handles SQLite layer (or read-only runtime mode) for vocab/bigrams. | `app._db_open_and_load(...)` |
| `_db_queue_update` | Gere la couche SQLite (ou son mode lecture seule) pour vocabulaire/bigrammes. | Handles SQLite layer (or read-only runtime mode) for vocab/bigrams. | `app._db_queue_update(...)` |
| `_db_flush` | Gere la couche SQLite (ou son mode lecture seule) pour vocabulaire/bigrammes. | Handles SQLite layer (or read-only runtime mode) for vocab/bigrams. | `app._db_flush(...)` |
| `_build_ui` | Coordonne le comportement UI clavier/souris et l'etat IA visible. | Coordinates keyboard/mouse UI behavior and visible AI state. | `app._build_ui(...)` |
| `_bind_keys` | Coordonne le comportement UI clavier/souris et l'etat IA visible. | Coordinates keyboard/mouse UI behavior and visible AI state. | `app._bind_keys(...)` |
| `confirm_discard_changes` | Gere le cycle de vie des fichiers texte et la protection des changements non sauvegardes. | Handles text file lifecycle and unsaved-change protection. | `app.confirm_discard_changes()` |
| `new_file` | Gere le cycle de vie des fichiers texte et la protection des changements non sauvegardes. | Handles text file lifecycle and unsaved-change protection. | `app.new_file()` |
| `open_file` | Gere le cycle de vie des fichiers texte et la protection des changements non sauvegardes. | Handles text file lifecycle and unsaved-change protection. | `app.open_file()` |
| `save_file` | Gere le cycle de vie des fichiers texte et la protection des changements non sauvegardes. | Handles text file lifecycle and unsaved-change protection. | `app.save_file()` |
| `save_as` | Gere le cycle de vie des fichiers texte et la protection des changements non sauvegardes. | Handles text file lifecycle and unsaved-change protection. | `app.save_as()` |
| `on_close` | Gere le cycle de vie des fichiers texte et la protection des changements non sauvegardes. | Handles text file lifecycle and unsaved-change protection. | `app.on_close()` |
| `set_status` | Supervise la disponibilite modele, les erreurs, et les parametres des appels Ollama. | Supervises model availability, errors, and Ollama call parameters. | `app.set_status(...)` |
| `_report_model_error` | Supervise la disponibilite modele, les erreurs, et les parametres des appels Ollama. | Supervises model availability, errors, and Ollama call parameters. | `app._report_model_error(...)` |
| `_predict_limit` | Supervise la disponibilite modele, les erreurs, et les parametres des appels Ollama. | Supervises model availability, errors, and Ollama call parameters. | `app._predict_limit(...)` |
| `_ensure_model_available` | Supervise la disponibilite modele, les erreurs, et les parametres des appels Ollama. | Supervises model availability, errors, and Ollama call parameters. | `app._ensure_model_available(...)` |
| `_ollama_chat` | Supervise la disponibilite modele, les erreurs, et les parametres des appels Ollama. | Supervises model availability, errors, and Ollama call parameters. | `app._ollama_chat(...)` |
| `clear_ai` | Coordonne le comportement UI clavier/souris et l'etat IA visible. | Coordinates keyboard/mouse UI behavior and visible AI state. | `app.clear_ai(...)` |
| `update_lang` | Extrait le contexte texte/curseur necessaire aux suggestions et corrections. | Extracts text/cursor context used by suggestions and corrections. | `app.update_lang()` |
| `get_context` | Extrait le contexte texte/curseur necessaire aux suggestions et corrections. | Extracts text/cursor context used by suggestions and corrections. | `app.get_context()` |
| `get_cursor_context` | Extrait le contexte texte/curseur necessaire aux suggestions et corrections. | Extracts text/cursor context used by suggestions and corrections. | `app.get_cursor_context()` |
| `get_prev_word` | Extrait le contexte texte/curseur necessaire aux suggestions et corrections. | Extracts text/cursor context used by suggestions and corrections. | `app.get_prev_word()` |
| `get_word_under_cursor` | Pilote les suggestions de mots locales/LLM et le popup de selection. | Drives local/LLM word suggestions and popup selection. | `app.get_word_under_cursor(...)` |
| `hide_ghost` | Controle le texte fantome gris (continuation/suffixe) et son positionnement. | Controls gray ghost text (continuation/suffix) and its positioning. | `app.hide_ghost(...)` |
| `update_ghost_position` | Controle le texte fantome gris (continuation/suffixe) et son positionnement. | Controls gray ghost text (continuation/suffix) and its positioning. | `app.update_ghost_position(...)` |
| `set_ghost` | Controle le texte fantome gris (continuation/suffixe) et son positionnement. | Controls gray ghost text (continuation/suffix) and its positioning. | `app.set_ghost(...)` |
| `_prepare_next_ghost` | Controle le texte fantome gris (continuation/suffixe) et son positionnement. | Controls gray ghost text (continuation/suffix) and its positioning. | `app._prepare_next_ghost(...)` |
| `_auto_space_after_accept` | Fonction utilitaire interne du flux principal de l'application. | Internal helper used by the main application flow. | `app._auto_space_after_accept(...)` |
| `_maybe_remove_space_before_punct` | Fonction utilitaire interne du flux principal de l'application. | Internal helper used by the main application flow. | `app._maybe_remove_space_before_punct(...)` |
| `hide_word_popup` | Pilote les suggestions de mots locales/LLM et le popup de selection. | Drives local/LLM word suggestions and popup selection. | `app.hide_word_popup(...)` |
| `show_word_popup` | Pilote les suggestions de mots locales/LLM et le popup de selection. | Drives local/LLM word suggestions and popup selection. | `app.show_word_popup(...)` |
| `reposition_word_popup` | Pilote les suggestions de mots locales/LLM et le popup de selection. | Drives local/LLM word suggestions and popup selection. | `app.reposition_word_popup(...)` |
| `accept_word` | Pilote les suggestions de mots locales/LLM et le popup de selection. | Drives local/LLM word suggestions and popup selection. | `app.accept_word(...)` |
| `on_up` | Fonction utilitaire interne du flux principal de l'application. | Internal helper used by the main application flow. | `app.on_up(...)` |
| `on_down` | Fonction utilitaire interne du flux principal de l'application. | Internal helper used by the main application flow. | `app.on_down(...)` |
| `on_ctrl_space` | Fonction utilitaire interne du flux principal de l'application. | Internal helper used by the main application flow. | `app.on_ctrl_space(...)` |
| `_update_hint` | Coordonne le comportement UI clavier/souris et l'etat IA visible. | Coordinates keyboard/mouse UI behavior and visible AI state. | `app._update_hint(...)` |
| `on_tab` | Coordonne le comportement UI clavier/souris et l'etat IA visible. | Coordinates keyboard/mouse UI behavior and visible AI state. | `app.on_tab(...)` |
| `_index_word` | Pilote les suggestions de mots locales/LLM et le popup de selection. | Drives local/LLM word suggestions and popup selection. | `app._index_word(...)` |
| `_rebuild_vocab_index` | Maintient l'index vocabulaire et calcule le ranking de suggestions locales. | Maintains vocab index and ranks local suggestions. | `app._rebuild_vocab_index(...)` |
| `schedule_vocab_rebuild` | Maintient l'index vocabulaire et calcule le ranking de suggestions locales. | Maintains vocab index and ranks local suggestions. | `app.schedule_vocab_rebuild(...)` |
| `rebuild_vocab` | Maintient l'index vocabulaire et calcule le ranking de suggestions locales. | Maintains vocab index and ranks local suggestions. | `app.rebuild_vocab(...)` |
| `local_candidates_scored` | Maintient l'index vocabulaire et calcule le ranking de suggestions locales. | Maintains vocab index and ranks local suggestions. | `app.local_candidates_scored(...)` |
| `on_key_release` | Coordonne le comportement UI clavier/souris et l'etat IA visible. | Coordinates keyboard/mouse UI behavior and visible AI state. | `app.on_key_release(...)` |
| `request_word_suggestions` | Pilote les suggestions de mots locales/LLM et le popup de selection. | Drives local/LLM word suggestions and popup selection. | `app.request_word_suggestions(...)` |
| `ask_word_suggestions_plain` | Pilote les suggestions de mots locales/LLM et le popup de selection. | Drives local/LLM word suggestions and popup selection. | `app.ask_word_suggestions_plain(...)` |
| `request_next_ghost` | Controle le texte fantome gris (continuation/suffixe) et son positionnement. | Controls gray ghost text (continuation/suffix) and its positioning. | `app.request_next_ghost(...)` |
| `ask_next_ghost_plain` | Controle le texte fantome gris (continuation/suffixe) et son positionnement. | Controls gray ghost text (continuation/suffix) and its positioning. | `app.ask_next_ghost_plain(...)` |
| `get_fix_region` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app.get_fix_region(...)` |
| `_fix_popup_size` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app._fix_popup_size(...)` |
| `_clamp_to_screen` | Gere la zone de correction, le popup preview, et les garde-fous qualite. | Handles correction region, preview popup, and quality guards. | `app._clamp_to_screen(...)` |
| `_reposition_fix_popup` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app._reposition_fix_popup(...)` |
| `hide_fix_popup` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app.hide_fix_popup(...)` |
| `show_fix_popup` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app.show_fix_popup(...)` |
| `underline_diffs` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app.underline_diffs(...)` |
| `apply_fix` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app.apply_fix(...)` |
| `_is_bad_fix` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app._is_bad_fix(...)` |
| `ask_block_fix_plain` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app.ask_block_fix_plain(...)` |
| `_linewise_fix` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app._linewise_fix(...)` |
| `request_block_fix` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app.request_block_fix(...)` |
| `correct_document` | Prepare, evalue, affiche et applique les corrections orthographe/grammaire. | Prepares, evaluates, previews, and applies spelling/grammar fixes. | `app.correct_document(...)` |

## Function Reference: `app/seed_db.py`
| Function | FR (ce que ca fait) | EN (what it does) | Exemple / Example |
|---|---|---|---|
| `seed_from_wordfreq` | Importe les mots frequents EN/FR depuis wordfreq dans SQLite. | Imports high-frequency EN/FR words from wordfreq into SQLite. | `seed_from_wordfreq(conn)` |
| `needs_seed` | Decide si la base doit etre reseed (vide, schema absent, force). | Decides whether DB reseeding is needed (empty/missing schema/forced). | `needs_seed(conn)` |
| `ensure_schema` | Cree les tables words/bigrams/lang_words si absentes. | Creates words/bigrams/lang_words tables if missing. | `ensure_schema(conn)` |
| `main` | Orchestration complete du seeding au demarrage. | Full startup seeding orchestration. | `python app/seed_db.py` |

## Configuration pratique / Practical config
FR: Variables utiles dans `.env` / environnement:
- `OLLAMA_MODEL`: modele cible (ex: `gemma3:1b`).
- `OLLAMA_HOST`: endpoint Ollama (`http://localhost:11434` en natif).
- `USE_SQLITE_VOCAB`: active le vocabulaire persistant SQLite.
- `USE_LLM_NEXT_GHOST`: active la completion fantome de continuation.
- `ENABLE_FUZZY`: active la recherche approximative (aide dyslexie).
EN: Useful `.env` / environment variables:
- `OLLAMA_MODEL`: target model name (for example `gemma3:1b`).
- `OLLAMA_HOST`: Ollama endpoint (`http://localhost:11434` in native mode).
- `USE_SQLITE_VOCAB`: enables persistent SQLite vocabulary.
- `USE_LLM_NEXT_GHOST`: enables next-word ghost continuation.
- `ENABLE_FUZZY`: enables approximate/fuzzy matching.

## Limitations importantes / Important limitations
FR:
- Le LLM peut proposer des sorties hors-sujet; des filtres existent mais ne sont pas parfaits.
- Les suggestions dependent de la qualite du vocabulaire seed et du contexte recent.
EN:
- The LLM can still produce off-target text; filters help but are not perfect.
- Suggestion quality depends on seed vocabulary and recent context quality.
