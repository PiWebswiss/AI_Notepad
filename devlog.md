# Dev Log - AI Notepad

## 2026-04-02

### Ajout de commentaires dans tous les fichiers

Ajout de commentaires explicatifs dans tous les fichiers du projet pour faciliter la comprehension et la maintenance du code.

**Fichiers modifies :**

- **run.ps1** : commentaires sur les variables (`$appDir`, `$venvPath`, `$shell`), les proprietes du raccourci desktop, et le sentinel pip.
- **cleanup.ps1** : commentaires sur les chemins d'artefacts locaux et l'image Docker.
- **app/db.py** : commentaires sur les constantes (`DB_FILE`, `ALLOW_UNKNOWN_WORDS`, `_ACCENT_RE`), les stopwords, le cache de langue, la detection de langue (scoring), et le filtrage par langue.
- **app/llm.py** : commentaires sur le cache client, le format de reponse Pydantic.
- **app/text_utils.py** : commentaires organises par sections (accent handling, text chunking, deduplication, LLM output cleaning, correction result checks, post-correction formatting). Explication des regex de nettoyage et des heuristiques de detection de chatbot.
- **app/suggestions.py** : commentaires inline sur chaque parametre de `rank_local_candidates`, explication des phases prefix matching et fuzzy matching, et du tri final.
- **app/ui.py** : commentaires sur le theme (palette de couleurs), les handles de debounce, les IDs de requete, l'etat des suggestions/corrections, les bindings clavier, les popups, et la barre d'indice.

### Nettoyage des espaces d'alignement

Suppression des espaces excessifs utilises pour aligner les `=` dans les scripts PowerShell et dans `ui.py`.

**Fichiers modifies :**

- **run.ps1** : `$root`, `$shell`, `$shortcut.*`, `$reqFile`.
- **cleanup.ps1** : `$venvPath`, `$dataPath`.

### Suppression du code de compatibilite ollama

Le projet installe toujours la derniere version de la librairie `ollama` via pip. Le code de compatibilite avec les anciennes versions (format `dict` vs Pydantic, `TypeError` fallback pour `timeout` et `think=False`) etait donc inutile.

**Fichiers modifies :**

- **app/llm.py** :
  - `get_ollama_client()` : suppression du `try/except TypeError` autour de `ollama.Client(host, timeout)`.
  - `extract_chat_content()` : suppression du chemin `isinstance(resp, dict)`, conserve uniquement `resp.message.content`.

- **app/ui.py** :
  - `_ensure_model_available()` : suppression du double chemin `dict`/Pydantic pour `data.list()` et `m.model`. Utilise directement `data.models` et `m.model`.
  - `_do_chat()` : suppression du `try/except TypeError` autour de `think=False`. Appel direct avec `think=False`.

### Ajout du point final dans post_fix_capitalization()

La fonction `post_fix_capitalization()` dans `text_utils.py` s'assurait deja que chaque phrase commence par une majuscule. Elle verifie maintenant aussi que le texte se termine par une ponctuation de fin de phrase (`.`, `!` ou `?`), et ajoute un point si ce n'est pas le cas.

### Correction du lancement (run.ps1 → ui.py)

Le fichier `app.py` a ete renomme en `ui.py` lors du refactoring en modules. Le script `run.ps1` pointait encore vers `app.py`, ce qui provoquait une erreur `No such file or directory` au lancement.

**Correction :** `run.ps1` ligne 144, `app.py` remplace par `ui.py`.

### Correction de l'encodage UTF-8 corrompu dans ui.py

Le fichier `ui.py` contenait des caracteres Unicode doublement encodes (mojibake). Les plages de caracteres accentues (`À-Ö`, `Ø-ö`, `ø-ÿ`) dans les regex et les guillemets typographiques (`'`, `"`) dans `PUNCT_CHARS` etaient illisibles par Python.

**Lignes corrigees :**

- **Ligne 195** (`PUNCT_CHARS`) : guillemets typographiques restaures (`'` et `"`).
- **Ligne 844** (`get_prev_word`) : regex de tokenisation avec plages accentuees corrigees.
- **Ligne 1157** (`rebuild_vocab`) : meme regex corrigee.
- **Ligne 1** : suppression d'un BOM (Byte Order Mark) invisible qui causait une `SyntaxError`.

### Simplification de la correction (suppression des stages 2 et 3)

La correction par bloc utilisait 3 stages : prompt normal, prompt strict (`strong=True`), puis correction ligne par ligne (`_linewise_fix`). En pratique seul le stage 1 etait utile. Les stages 2 et 3 ont ete supprimes.

**Modifications :**

- **app/ui.py** :
  - `ask_block_fix_plain()` : suppression du parametre `strong` et du texte additionnel "Renvoie TOUT le texte, ligne par ligne".
  - `_linewise_fix()` : methode supprimee entierement.
  - `request_block_fix()` : simplifie a un seul appel au lieu de 3 stages.
  - `correct_document()` : meme simplification par chunk.

### Suppression du Dockerfile et des services Docker inutilises

L'application tourne nativement sur le PC (via `run.ps1` ou `run.sh`). Seul Ollama a besoin de Docker. Le Dockerfile et les services `app` et `ollama_init` n'etaient jamais utilises.

**Modifications :**

- **app/Dockerfile** : supprime.
- **docker-compose.yml** : services `app` et `ollama_init` supprimes. Ne reste que le service `ollama`.
- **run.sh** : reecrit pour suivre le meme flux que `run.ps1` (Python natif, Ollama seul dans Docker). L'ancien script utilisait X11 et un conteneur app qui n'existent plus.
- **run.ps1**, **requirements.txt** : references a `app.py` corrigees en `ui.py`.

### Correction du commentaire .env

Le commentaire dans `.env` disait "override the default model chosen in app/app.py". Le modele est defini uniquement dans `.env`, il n'y a pas de valeur par defaut dans le code. Commentaire corrige.
