-- ============================================================
-- AI Notepad - demonstration du systeme de base de donnees
-- ============================================================


-- ========== 1. Etat de la base ==========

-- Nombre total de mots dans le vocabulaire.
SELECT COUNT(*) FROM words;

-- Nombre de bigrammes appris par l'utilisateur.
SELECT COUNT(*) FROM bigrams;


-- ========== 2. Requete de lecture au demarrage ==========

-- Charge en memoire les 150 000 mots les plus frequents.
SELECT word, freq
FROM words
ORDER BY freq DESC
LIMIT 150000;


-- ========== 3. Recherche contextuelle via bigrammes ==========

-- Liste les mots qui ont suivi "je", classes par frequence d'apparition de la paire.
SELECT w.word, b.freq
FROM bigrams b
JOIN words prev ON prev.id = b.prev_id
JOIN words w    ON w.id    = b.next_id
WHERE prev.word = 'je'
ORDER BY b.freq DESC
LIMIT 10;


-- ========== 4. Demonstration : effet du bigramme sur le classement ==========

-- Sans bigramme : classement par frequence seule.
-- "sur" arrive en tete car c'est un mot globalement plus frequent que "suis".
SELECT word, freq
FROM words
WHERE word LIKE 'su%' AND lang = 'fr'
ORDER BY freq DESC
LIMIT 5;


-- Avec bigramme : on simule 50 occurrences de la paire (je, suis) pour illustrer
-- un utilisateur ayant regulierement ecrit "je suis".
-- Score = unigram + 8 x bigram.
SELECT w.word,
       w.freq                                                        AS unigram,
       CASE WHEN w.word = 'suis' THEN 50 ELSE 0 END                  AS bigram,
       w.freq + 8 * CASE WHEN w.word = 'suis' THEN 50 ELSE 0 END     AS score
FROM words w
WHERE w.word LIKE 'su%' AND w.lang = 'fr'
ORDER BY score DESC
LIMIT 5;
