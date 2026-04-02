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
