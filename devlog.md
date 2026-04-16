# Dev Log - AI Notepad

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

### Remplacement de la boucle de retry par un healthcheck Docker

Les scripts de lancement utilisaient une boucle qui reessayait `ollama list` jusqu'a 20 fois (1 seconde entre chaque tentative) pour attendre que le serveur Ollama soit pret. Cette approche a ete remplacee par un healthcheck Docker natif.

**Modifications :**

- **docker-compose.yml** : ajout d'un healthcheck sur le service `ollama` qui ping `http://localhost:11434/` toutes les 2 secondes.
- **run.ps1** : la boucle `for ($i = 0; $i -lt 20; ...)` remplacee par `docker compose up -d --wait ollama`, qui attend que le healthcheck passe avant de continuer.
- **run.sh** : meme remplacement de la boucle `for i in $(seq 1 20)` par `--wait`.

### Raccourci bureau deplace en fin de script

La creation du raccourci bureau (question + creation) etait faite au debut du script de lancement. Si l'installation plantait ensuite, l'utilisateur se retrouvait avec un raccourci vers une app cassee. La question est maintenant posee au debut, mais le raccourci n'est cree qu'a la fin, une fois que toute l'installation s'est terminee avec succes.

**Fichiers modifies :** `run.ps1`, `run.sh`.

### Correction du bug "stale" sur la correction automatique

Les corrections etaient systematiquement rejetees comme "stale" car le `doc_version` changeait a chaque touche, meme si le texte du bloc n'avait pas change. Le collage (paste) incrementait aussi le compteur plusieurs fois.

**Correction :** le check de fraicheur compare maintenant le texte reel du bloc au lieu du `doc_version`. Si le texte n'a pas change depuis la requete, la correction est acceptee.

**Fichier modifie :** `app/ui.py` — `request_block_fix()`.

### Ajout d'un indicateur de chargement (spinner)

Ajout d'une animation rotative (`| / - \`) dans la barre de statut pendant que l'IA travaille sur une correction. L'animation demarre quand la requete est envoyee et s'arrete quand la reponse arrive.

**Fichier modifie :** `app/ui.py` — nouvelles methodes `_start_spinner()` et `_stop_spinner()`, utilisees dans `request_block_fix()` et `correct_document()`.

### Utilisation de split_into_chunks pour la correction auto

La correction automatique pendant la frappe (`request_block_fix`) envoyait le paragraphe entier en un seul bloc au modele. Pour les longs textes colles sans lignes vides, cela pouvait depasser la capacite du modele (4096 tokens de contexte).

La correction auto utilise maintenant `split_into_chunks()` pour decouper les longs blocs en morceaux de 1600 caracteres, comme le fait deja le bouton Correct All. Les morceaux sont corriges un par un puis reassembles avant d'etre affiches dans un seul popup.

La constante `MAX_FIX_CHARS` (ancienne limite de troncature) a ete supprimee car le decoupage en chunks rend la troncature inutile.

### Ajout d'un spinner graphique

Ajout d'une animation de chargement (arc qui tourne) dans la barre d'outils pendant que l'IA corrige le texte. Le spinner apparait a gauche du texte de statut et disparait quand la reponse arrive.

**Fichier modifie :** `app/ui.py` — nouvelles methodes `_build_spinner()`, `_start_spinner()` et `_stop_spinner()` utilisant un Canvas Tkinter.

### Popup de correction agrandi

Le popup de correction etait trop petit pour afficher tout le texte corrige. Les dimensions maximales ont ete augmentees (720x420 -> 900x550) pour montrer plus de contenu sans scroller.

### Audit complet et corrections

Un audit ligne par ligne de tous les fichiers a revele 5 problemes :

- **Critique : `correct_document()` cassee** — La methode utilisait encore `strong=True` et `_linewise_fix()` qui avaient ete supprimes. Corrige pour utiliser le meme flux simplifie que `request_block_fix()`.
- **Doublons dans `_FR_APOST_PREFIXES`** (db.py) — Le tuple contenait 20 entrees au lieu de 10 : les memes prefixes etaient dupliques. Remplace par 10 variantes apostrophe droite (`'`) + 10 variantes apostrophe courbe (`\u2019`).
- **Constante inutilisee `ALLOW_UNKNOWN_WORDS`** (ui.py) — Definie dans ui.py mais jamais utilisee (db.py la lit directement depuis l'environnement). Supprimee.
- **Mojibake dans les commentaires** (ui.py) — Des tirets em-dash corrompus dans les commentaires ghost_mode (lignes 324-326). Remplaces par `--`.
- **Mojibake dans une string** (ui.py) — Le caractere ellipsis dans `"Correcting..."` etait corrompu. Remplace par `...`.
- **Schema SQL duplique** (ui.py) — Les `CREATE TABLE` et `CREATE INDEX` etaient presents dans ui.py alors que seed_db.py les cree deja. Supprimes de ui.py.

### Suppression du code mort (ghost next + LLM word suggestions)

Deux fonctionnalites etaient presentes dans le code mais desactivees par defaut et jamais utilisees :

**Ghost continuation (Copilot-like)** — supprime :
- Constantes : `USE_LLM_NEXT_GHOST`, `NEXT_GHOST_DEBOUNCE_MS`, `NEXT_GHOST_MAX_CHARS`, `NEXT_GHOST_MIN_INPUT`, `NEXT_GHOST_CONTEXT_CHARS`.
- Methodes : `request_next_ghost()`, `ask_next_ghost_plain()`, `_prepare_next_ghost()`.
- Variables : `_after_next`, `_ghost_req`.
- Le mode ghost `"next"` n'existe plus, seul `"word"` (suffix de suggestion) reste.

**LLM word suggestions** — supprime :
- Constante : `USE_LLM_WORD_SUGGESTIONS`, `WORD_DEBOUNCE_MS`.
- Methodes : `request_word_suggestions()`, `ask_word_suggestions_plain()`.
- Variables : `_after_word`, `_word_req`, `word_cache`.
- `on_ctrl_space()` simplifie pour juste cycler les suggestions locales.
- `get_cursor_context()` supprime (jamais appelee).

Les suggestions de mots viennent uniquement du vocabulaire SQLite local, pas du LLM.

### Amelioration des commentaires dans ui.py

Ajout de commentaires dans le style de `text_utils.py` (sections `# ---`, explication du "pourquoi") pour que le code soit comprehensible par quelqu'un qui le lit pour la premiere fois. Commentaires ajoutes sur les imports, la boucle de frappe, les guards de correction, le prompt systeme, le spinner, et les methodes de statut.

### Remise du fallback think=False dans _do_chat()

Le parametre `think=False` empeche les modeles "thinking" (comme qwen3) de gaspiller des tokens en blocs de reflexion `<think>...</think>`. Mais les modeles qui ne supportent pas ce parametre (comme gemma4) provoquaient une erreur silencieuse. Le `try/except TypeError` a ete remis pour gerer les deux cas : les modeles thinking recoivent `think=False`, les autres l'ignorent.

### Changement de modele : gemma4:e2b

Le modele a ete change de `qwen3:1.7b` a `gemma4:e2b` (5.1B parametres, architecture gemma4 de Google). Le modele qwen3 est optimise pour le raisonnement logique, pas pour la correction de texte. gemma4 est meilleur pour suivre des instructions comme "corrige ce texte".

## 2026-04-05

### Correction du popup de correction qui ne s'affichait pas

Le popup de correction (preview) ne s'affichait pas apres un copier-coller ou dans certains cas normaux, bien que le texte en rouge (underlines) apparaisse correctement. Deux bugs identifies :

1. **Ordre d'appel incorrect dans `show_fix_popup()`** — `_reposition_fix_popup()` etait appele avant `deiconify()`. Or `_reposition_fix_popup()` verifie `winfo_viewable()` en premier et retourne immediatement si le popup n'est pas visible. Le popup etait donc rendu visible sans jamais avoir ete positionne. Correction : appeler `deiconify()` puis `update_idletasks()` puis `_reposition_fix_popup()`.

2. **Curseur hors ecran = popup cache** — Dans `_reposition_fix_popup()`, si `bbox("insert")` retournait `None` (curseur hors de la zone visible, typiquement apres un collage de texte long), le popup etait cache au lieu d'etre positionne. Correction : le popup est maintenant centre sur le widget texte en fallback au lieu d'etre cache.

**Fichier modifie :** `app/ui.py` — methodes `show_fix_popup()` et `_reposition_fix_popup()`.

### Erreurs modele visibles au lieu de "No correction needed"

Quand le modele echouait (Ollama down, timeout, etc.), l'application affichait "No correction needed" au lieu d'une erreur. Le code attrapait l'exception silencieusement et renvoyait le texte original, ce qui declenchait le message "No correction needed".

Corrections :
- Les workers de `request_block_fix()` et `correct_document()` tracent maintenant si une exception a eu lieu (`had_error`). Si oui, le status affiche "Model error" au lieu de "No correction needed".
- `SHOW_MODEL_ERRORS_IN_STATUS` active par defaut (etait desactive).

**Fichier modifie :** `app/ui.py`.

### Protection "Correct All" sans texte

Appuyer sur "Correct All" avec un editeur vide envoyait une requete inutile au modele. Le texte est maintenant verifie avant tout appel au modele, et le status affiche "No text to correct".

**Fichier modifie :** `app/ui.py` — methode `correct_document()`.

### Raccourci bureau sans console

Le raccourci bureau lancait PowerShell en fenetre minimisee (`WindowStyle = 7`), ce qui laissait une icone dans la barre des taches. Change en fenetre cachee (`-WindowStyle Hidden`, `WindowStyle = 0`) pour que seule l'application Tkinter apparaisse.

**Fichier modifie :** `run.ps1`.

### Messages de lancement plus clairs pour le modele

Le script affichait "Ensuring model..." a chaque lancement, meme quand le modele etait deja present. Remplace par deux messages distincts : "Model already available." ou "Model not found. Downloading...".

**Fichiers modifies :** `run.ps1`, `run.sh`.

### Healthcheck Docker corrige

Le healthcheck utilisait `curl` qui n'est pas installe dans l'image Ollama. Le conteneur etait donc toujours marque `(unhealthy)`. Remplace par `ollama list` qui est garanti present dans l'image.

**Fichier modifie :** `docker-compose.yml`.

### Pseudo-code reecrit en francais

Le diagramme SVG contenait des descriptions informelles. Reecrit en vrai pseudo-code francais avec les mots-cles standards (DEBUT, FIN, TANT QUE, SI, ALORS, ATTENDRE, ENVOYER, RECEVOIR, AFFICHER, APPLIQUER). Suppression des ":" et "+". L'etape 7 (verification de la correction) clarifiee : c'est l'application qui filtre les mauvaises sorties, pas le modele.

**Fichier modifie :** `images/psedo_code.xml`.

### Support GPU automatique

Ajout du bloc `deploy.resources.reservations.devices` dans `docker-compose.yml` pour activer l'acceleration GPU NVIDIA automatiquement quand disponible. Sur les systemes sans GPU (ou sans nvidia-container-toolkit), Docker ignore ce bloc et tourne sur CPU. Aucune configuration manuelle requise.

**Fichiers modifies :** `docker-compose.yml`, `README.md` (section "GPU acceleration").

### Corrections README

- Typo corrigee : `dc AI_Notepad` -> `cd AI_Notepad`.
- Liens ajoutes vers les installateurs de Docker Desktop et Python dans la section Prerequisites.

**Fichier modifie :** `README.md`.
