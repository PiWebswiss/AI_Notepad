# Dev Log — AI Notepad

Journal des modifications apportées au projet, regroupées par thème.

---

## Infrastructure et scripts de lancement

### Renommage de `app.py` en `ui.py`

Lors du refactoring en modules, le fichier principal a été renommé `app.py` → `ui.py`. `run.ps1`, `run.sh` et `requirements.txt` pointaient encore vers l'ancien nom, ce qui provoquait une erreur `No such file or directory` au lancement. Toutes les références ont été mises à jour.

### Suppression du Dockerfile et des services Docker inutilisés

L'application Tkinter tourne nativement sur l'hôte (via `run.ps1` ou `run.sh`) — seul Ollama a besoin de Docker. Le `app/Dockerfile` et les services `app` et `ollama_init` du `docker-compose.yml` n'étaient jamais utilisés, ils ont été supprimés. Le `run.sh` a été réécrit pour suivre le même flux que `run.ps1` (Python natif + Ollama seul dans Docker) — l'ancienne version utilisait X11 et un conteneur app qui n'existaient plus.

### Détection GPU automatique

Le bloc `deploy.resources.reservations.devices` fixé dans `docker-compose.yml` provoquait une erreur `could not select device driver "nvidia"` sur toute machine sans NVIDIA Container Toolkit (VM, laptop sans GPU, CI). Remplacé par une variable `${DOCKER_RUNTIME:-runc}` dans le champ `runtime`, pilotée par `run.sh` / `run.ps1` qui détectent `nvidia-smi` + runtime nvidia Docker au lancement. GPU activé automatiquement sur les machines équipées, fallback CPU propre ailleurs.

### Healthcheck Docker pour Ollama

Les scripts de lancement utilisaient une boucle qui réessayait `ollama list` jusqu'à 20 fois (1 s entre chaque tentative) pour attendre que le serveur Ollama soit prêt. Remplacé par un healthcheck Docker natif (ping `ollama list` toutes les 2 s) et un `docker compose up -d --wait ollama` qui bloque jusqu'à ce que le healthcheck passe. Le healthcheck utilisait initialement `curl` absent de l'image Ollama — corrigé pour utiliser la commande `ollama list` garantie présente.

### Sentinel pip déplacé dans le venv

Le fichier `.deps-installed` vivait à la racine du projet. Si le `.venv` était supprimé ou manquant (copie projet sans venv, rsync vers un Pi), le sentinel restait → `run.sh` créait un venv vide mais sautait `pip install` → crash au démarrage sur `ModuleNotFoundError`. Le sentinel est maintenant dans `$VENV_PATH/.deps-installed` ; son cycle de vie est lié au venv.

### Check tkinter en amont dans `run.sh`

Si `python3-tk` manquait sur Linux, l'utilisateur subissait tout le pipeline (venv + pip install + seed_db) avant un traceback Python obscur. Ajout d'un check `python3 -c "import tkinter"` avant la création du venv, avec message clair par distro (apt / dnf / pacman).

### `DB_FILE` et `OLLAMA_HOST` respectent l'environnement utilisateur

Les scripts faisaient `export DB_FILE=...` sans fallback, écrasant toute valeur déjà définie par l'utilisateur. Remplacé par `${DB_FILE:-default}` en bash et `if (-not $env:DB_FILE)` en PowerShell.

### Parsing `.env` plus robuste

Le parser sed de `run.sh` ne retirait pas les guillemets entourants. `OLLAMA_MODEL="gemma3:4B"` devenait `"gemma3:4B"` littéralement, incluant les quotes. Ajout d'un sed pour strip les guillemets simples et doubles.

### Raccourci bureau déplacé en fin de script

La création du raccourci bureau était faite au début du script. Si l'installation plantait ensuite, l'utilisateur se retrouvait avec un raccourci vers une app cassée. La question est maintenant posée au début, mais le raccourci n'est créé qu'à la fin, une fois l'installation complètement réussie. Sur Windows, le raccourci lance PowerShell en fenêtre cachée (`-WindowStyle Hidden`) pour que seule l'application Tkinter apparaisse.

### Messages de lancement plus clairs

Le script affichait `Ensuring model...` à chaque lancement, même quand le modèle était déjà présent. Remplacé par deux messages distincts : `Model already available.` ou `Model not found. Downloading...`.

### Cleanup legacy supprimé

Après le déplacement du sentinel dans le venv, le code qui supprimait l'ancien sentinel à la racine du projet n'avait plus d'utilité. Retiré de `cleanup.sh` et `cleanup.ps1`.

---

## Interface utilisateur et rendu cross-platform

### Auto-résolution des polices par plateforme

Les polices `Segoe UI` et `Cascadia Code` étaient codées en dur dans `ui.py`, alors qu'elles n'existent pas sur Linux. Remplacées par 3 constantes (`FONT_FAMILY_UI`, `FONT_FAMILY_UI_SEMIBOLD`, `FONT_FAMILY_MONO`) résolues au démarrage via `tkinter.font.families()` avec des chaînes de fallback : `Segoe UI → Noto Sans → DejaVu Sans`, `Cascadia Code → Cascadia Mono → DejaVu Sans Mono`.

### Installation automatique de `fonts-cascadia-code` sur Linux

Sur Linux, `run.sh` détecte si `fonts-cascadia-code` est absent et le propose via `apt-get install`. Best-effort, skippé silencieusement si `sudo`, `apt-get` ou le paquet ne sont pas disponibles. Permet l'alignement visuel de l'éditeur avec la version Windows.

### Scaling DPI sur Linux

Tk utilise 72 DPI par défaut sur X11, ce qui fait rendre tous les widgets et polices plus petits que sur Windows (qui remonte le vrai DPI). Ajout d'un `self.tk.call("tk", "scaling", 1.333)` sur non-Windows juste après `super().__init__()` pour aligner le rendu Linux sur la baseline Windows 96 DPI.

### Bordures de boutons supprimées sur Linux

`tk.Button` dessinait une bordure visible et un anneau de focus sur Linux (X11) même avec `relief="flat"`. Ajout de `borderwidth=0` et `highlightthickness=0` sur les trois `tk.Button` (toolbar, popup de mots, bouton X). Hover effect manuel via `<Enter>` / `<Leave>` sur les boutons toolbar car `activebackground` n'est pas appliqué au survol sur Linux Tk.

### Documentation de la dépendance système tkinter

`requirements.txt` a une en-tête documentant que `tkinter` n'est pas installable via pip et donnant les commandes d'installation par distro. Section « Linux — additional system packages » ajoutée au README avec les commandes d'installation et de désinstallation.

### Popup de correction agrandi

Le popup de correction était trop petit pour afficher tout le texte corrigé. Dimensions maximales augmentées de 720×420 à 900×550 pour montrer plus de contenu sans scroller.

### Affichage du popup après copier-coller

Le popup de correction ne s'affichait pas après un copier-coller ou dans certains cas normaux, bien que les soulignements rouges apparaissent correctement. Deux bugs corrigés :

- **Ordre d'appel dans `show_fix_popup()`** : `_reposition_fix_popup()` était appelé avant `deiconify()`. Or `_reposition_fix_popup()` vérifie `winfo_viewable()` et retourne immédiatement si le popup n'est pas visible → le popup apparaissait sans jamais avoir été positionné. Correction : `deiconify()` → `update_idletasks()` → `_reposition_fix_popup()`.
- **Curseur hors écran** : quand `bbox("insert")` retournait `None` (typiquement après un collage long), le popup était caché au lieu d'être positionné. Le popup est maintenant centré sur le widget texte en fallback.

### Spinner de chargement

Ajout d'une animation rotative dans la barre de statut pendant que l'IA travaille sur une correction. L'animation démarre quand la requête est envoyée et s'arrête quand la réponse arrive. Implémenté avec un Canvas Tkinter dessinant un arc qui tourne.

---

## Correction par LLM

### Simplification de la correction (stages 2 et 3 supprimés)

La correction par bloc utilisait trois stages : prompt normal, prompt strict (`strong=True`), puis correction ligne par ligne (`_linewise_fix`). En pratique seul le stage 1 était utile. Les stages 2 et 3 ont été supprimés, la méthode `_linewise_fix()` aussi, ce qui a grandement simplifié `request_block_fix()` et `correct_document()`.

### Découpage en chunks pour les longs textes

La correction automatique pendant la frappe envoyait le paragraphe entier en un seul bloc au modèle. Pour les longs textes collés sans lignes vides, cela pouvait dépasser la capacité du modèle (4096 tokens de contexte). Elle utilise maintenant `split_into_chunks()` pour découper les longs blocs en morceaux de 1600 caractères, comme le bouton « Correct All ». Les morceaux sont corrigés un par un puis réassemblés avant affichage. La constante `MAX_FIX_CHARS` (ancienne limite de troncature) a été supprimée.

### Correction du bug « stale »

Les corrections étaient systématiquement rejetées comme « stale » car le `doc_version` changeait à chaque touche, même si le texte du bloc n'avait pas changé. Le collage incrémentait aussi le compteur plusieurs fois. Le check de fraîcheur compare maintenant le texte réel du bloc au lieu du `doc_version`. Si le texte n'a pas changé depuis la requête, la correction est acceptée.

### Protection « Correct All » sans texte

Appuyer sur « Correct All » avec un éditeur vide envoyait une requête inutile au modèle. Le texte est maintenant vérifié avant tout appel au modèle, et le status affiche « No text to correct ».

### Erreurs modèle visibles au lieu de « No correction needed »

Quand le modèle échouait (Ollama down, timeout, etc.), l'application affichait « No correction needed » au lieu d'une erreur. Le code attrapait l'exception silencieusement et renvoyait le texte original. Les workers tracent maintenant si une exception a eu lieu (`had_error`). Si oui, le status affiche « Model error » au lieu du message trompeur. `SHOW_MODEL_ERRORS_IN_STATUS` a été activé par défaut.

### Simplification des options Ollama

L'ancienne logique `_predict_limit()` avec ses nombres magiques (`+500` pour les modèles thinking, `+60` d'overhead, `/3` ratio, `OLLAMA_NUM_PREDICT_MIN`/`MAX`) a été entièrement supprimée. Seul `temperature=0.0` reste passé explicitement à Ollama (indispensable pour avoir des corrections déterministes). `num_ctx` et `num_predict` sont laissés aux défauts du Modelfile du modèle.

### `keep_alive` pour éviter les cold starts

Ollama décharge le modèle après 5 min d'inactivité par défaut. Chaque correction après une pause payait alors un reload de 60+ secondes. Ajout de `keep_alive="30m"` dans `_do_chat()` pour garder le modèle en VRAM entre les appels.

### Préchauffage du modèle au démarrage

Au lancement de l'app, un thread de fond envoie une requête factice (`"hi"` avec `num_predict=1`) pour forcer le chargement du modèle en VRAM. Pendant que l'utilisateur tape ses premières lignes, Ollama finit de charger. Quand la première pause arrive, le modèle est déjà prêt — plus de 60 s d'attente au premier usage.

### Fallback `think=False` pour les modèles non-thinking

Le paramètre `think=False` empêche les modèles « thinking » (comme qwen3) de gaspiller des tokens en blocs de réflexion `<think>...</think>`. Les modèles qui ne supportent pas ce paramètre provoquaient une erreur silencieuse. Un `try/except TypeError` gère maintenant les deux cas : les modèles thinking reçoivent `think=False`, les autres l'ignorent.

### Correction du bug de ponctuation empilée (`!.` et `.!`)

Quand l'utilisateur tapait `.` et que le LLM ajoutait `!` pour emphase, le texte corrigé affichait `!.` ou `.!`. Ajout dans `post_fix_spacing()` de deux regex qui collapse ces mélanges vers `.` (la ponctuation neutre de l'utilisateur privilégiée sur l'emphase ajoutée par le LLM). Les ellipses (`...`, `...!`, `!...`) sont préservées via des guards de lookahead / lookbehind.

### Point final ajouté dans `post_fix_capitalization()`

La fonction s'assurait déjà que chaque phrase commence par une majuscule. Elle vérifie maintenant aussi que le texte se termine par une ponctuation de fin de phrase (`.`, `!` ou `?`), et ajoute un point si ce n'est pas le cas.

### Analyse performance : Gemma 3 4B sur RTX 3050 4 Go

Les logs Ollama révèlent que `gemma3:4B` (Q4_K_M, ~3,6 Go) ne tient pas entièrement dans les 4 Go de VRAM d'une RTX 3050 Laptop après l'overhead Windows. Résultat : Ollama split le modèle en `1,8 GiB GPU` + `1,8 GiB CPU`, ce qui ralentit l'inférence (transferts VRAM / RAM constants). Le modèle reste utilisable mais avec une vitesse réduite. Pour une vitesse full-GPU, utiliser `gemma3:1B` via `.env` (~700 Mo, tient entièrement en VRAM). Sur des GPU ≥ 6 Go de VRAM, le 4B passe en full-GPU et atteint sa vitesse nominale.

---

## Vocabulaire et base SQLite

### Fallback SQLite pour les mots hors du cache mémoire

Au démarrage, seuls les 150 000 mots les plus fréquents sont chargés en RAM pour limiter l'empreinte mémoire. Les ~50 000 mots restants en base (issus du seed `wordfreq`) étaient inaccessibles aux suggestions. Ajout d'un fallback : si la recherche RAM ne retourne aucun candidat et que le fragment fait ≥ 3 caractères, une requête SQL est faite sur la table `words` ; les résultats sont ajoutés au cache RAM et ré-classés avec le même algorithme de ranking (fréquence unigramme + bonus bigramme). Les mots rares fraîchement chargés restent en RAM pour la session et sont sauvegardés à la fermeture.

---

## Qualité du code et audit

### Audit ligne par ligne et corrections

Un audit complet de tous les fichiers a révélé plusieurs problèmes :

- **`correct_document()` cassée** — utilisait encore `strong=True` et `_linewise_fix()` qui avaient été supprimés. Corrigée pour suivre le flux simplifié de `request_block_fix()`.
- **Doublons dans `_FR_APOST_PREFIXES`** (`db.py`) — le tuple contenait 20 entrées au lieu de 10. Remplacé par 10 variantes apostrophe droite + 10 variantes apostrophe courbe.
- **Constante inutilisée `ALLOW_UNKNOWN_WORDS`** (`ui.py`) — définie mais jamais utilisée (`db.py` la lit directement depuis l'environnement). Supprimée.
- **Mojibake dans les commentaires** (`ui.py`) — tirets em-dash corrompus dans les commentaires `ghost_mode`. Remplacés par `--`.
- **Mojibake dans `"Correcting..."`** — caractère ellipsis corrompu. Remplacé par `...`.
- **Schéma SQL dupliqué** (`ui.py`) — `CREATE TABLE` et `CREATE INDEX` étaient présents dans `ui.py` alors que `seed_db.py` les crée déjà. Supprimés de `ui.py`.

### Correction de l'encodage UTF-8 corrompu dans `ui.py`

Le fichier contenait des caractères Unicode doublement encodés (mojibake). Les plages de caractères accentués (`À-Ö`, `Ø-ö`, `ø-ÿ`) dans les regex et les guillemets typographiques dans `PUNCT_CHARS` étaient illisibles par Python. Les regex de `get_prev_word` et `rebuild_vocab`, ainsi que le `PUNCT_CHARS`, ont été restaurés. Suppression d'un BOM invisible en ligne 1 qui causait une `SyntaxError`.

### Suppression du code de compatibilité Ollama

Le projet installe toujours la dernière version de la librairie `ollama` via pip. Le code de compatibilité avec les anciennes versions (format `dict` vs Pydantic, `TypeError` fallback pour `timeout`) était inutile. Nettoyé dans `llm.py` (`get_ollama_client`, `extract_chat_content`) et `ui.py` (`_ensure_model_available`).

### Suppression du code mort

Deux fonctionnalités étaient présentes dans le code mais désactivées par défaut et jamais utilisées :

- **Ghost continuation (style Copilot)** — constantes `USE_LLM_NEXT_GHOST`, `NEXT_GHOST_*`, méthodes `request_next_ghost()`, `ask_next_ghost_plain()`, `_prepare_next_ghost()`, variables `_after_next`, `_ghost_req`. Seul le mode ghost `"word"` (suffixe de suggestion) reste.
- **LLM word suggestions** — constantes `USE_LLM_WORD_SUGGESTIONS`, `WORD_DEBOUNCE_MS`, méthodes `request_word_suggestions()`, `ask_word_suggestions_plain()`, variables `_after_word`, `_word_req`, `word_cache`. `on_ctrl_space()` simplifié pour cycler uniquement les suggestions locales.

Les suggestions de mots viennent exclusivement du vocabulaire SQLite local, jamais du LLM.

### Ajout de commentaires explicatifs

Commentaires ajoutés dans tous les fichiers pour faciliter la compréhension et la maintenance :

- `run.ps1`, `cleanup.ps1` : variables, propriétés du raccourci desktop, sentinel pip, chemins d'artefacts, image Docker.
- `app/db.py` : constantes (`DB_FILE`, `ALLOW_UNKNOWN_WORDS`, `_ACCENT_RE`), stopwords, cache de langue, scoring et filtrage par langue.
- `app/llm.py` : cache client, format de réponse Pydantic.
- `app/text_utils.py` : sections (accent handling, chunking, deduplication, LLM output cleaning, etc.), explication des regex et des heuristiques de détection de chatbot.
- `app/suggestions.py` : paramètres inline de `rank_local_candidates`, phases prefix / fuzzy matching, tri final.
- `app/ui.py` : palette de couleurs, handles de debounce, IDs de requête, états des suggestions / corrections, bindings clavier, popups, barre d'indice, imports, boucle de frappe, guards de correction, prompt système, spinner, méthodes de statut.

### Nettoyage cosmétique

Suppression des espaces excessifs utilisés pour aligner les `=` dans les scripts PowerShell et dans `ui.py` (`$root`, `$shell`, `$shortcut.*`, `$reqFile`, `$venvPath`, `$dataPath`).

---

## Documentation

### Pseudo-code réécrit en français

Le diagramme SVG contenait des descriptions informelles. Réécrit en vrai pseudo-code français avec les mots-clés standards (DÉBUT, FIN, TANT QUE, SI, ALORS, ATTENDRE, ENVOYER, RECEVOIR, AFFICHER, APPLIQUER). Suppression des `:` et `+`. L'étape 7 (vérification de la correction) clarifiée : c'est l'application qui filtre les mauvaises sorties, pas le modèle.

### Corrections README

- Typo : `dc AI_Notepad` → `cd AI_Notepad`.
- Liens ajoutés vers les installateurs de Docker Desktop et Python dans la section Prerequisites.
- Section Linux avec les commandes d'installation et de désinstallation des paquets système requis.

### Correction du commentaire `.env`

Le commentaire disait `override the default model chosen in app/app.py`. Le modèle est défini uniquement dans `.env`, il n'y a pas de valeur par défaut dans le code. Commentaire corrigé.
