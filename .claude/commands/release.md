# Release de HOTAS Kneeboard

Tu guides David pas à pas pour sortir une nouvelle version de HOTAS Kneeboard, sur le modèle du `/release` de VEAF-Mission-Creation-Tools (VMCT).
Une étape à la fois : là où une étape attend une réponse de David, tu t'arrêtes et tu attends.

---

## Le contexte

- `develop` reçoit le travail par des PR ; `main` ne reçoit que des releases.
- Une release, ce sont deux PR :
  1. `chore/RELEASE-X.Y.Z` → `develop` : le numéro, le CHANGELOG, les notes, les captures ;
  2. `develop` → `main`, titrée `Release X.Y.Z`, fusionnée par un **vrai commit de fusion** (jamais en squash : `main` et `develop` doivent garder une histoire commune).
- La publication est automatique : à la fusion dans `main`, `.github/workflows/release.yml` construit l'exe sous Windows, crée le tag `vX.Y.Z` et publie la release GitHub avec `RELEASE_NOTES.md` (tel qu'il est dans le commit fusionné), plus le lien vers la documentation de la version.
  Le même push publie la documentation versionnée et l'alias `latest` (`.github/workflows/docs.yml`, mike).
  Pas de tag à pousser à la main.
- `release.yml` refuse de publier si `pyproject.toml` et `hotas_kneeboard/__init__.py` ne disent pas la même version, ou si le titre de `RELEASE_NOTES.md` ne finit pas par ce numéro.
  Une fusion dans `main` sans changement de version ne publie rien.
- Les PR de lot écrivent leurs entrées à la fin de `## [Unreleased]` et ne touchent jamais la version : le commit de release est le seul endroit où elle bouge.
  `tests/test_changelog.py` le garde.

---

## Étape 1 : ce qui part

1. `git fetch` puis `git pull --ff-only` sur `develop`.
2. Lis la section `## [Unreleased]` de `CHANGELOG.md`, et la liste des PR fusionnées depuis la dernière release (`gh pr list --state merged --base develop`, à partir de la date de la dernière release, `gh release list`).
   Signale ce qui manque au CHANGELOG, s'il manque quelque chose.
3. Vérifie que rien n'attend : PR ouvertes vers `develop`, lots `🔄 in-progress` ou `🧑 waiting-human` qui devraient partir avec cette version.
   Ne décide pas à la place de David : liste-les, avec ta reco.
4. Propose le numéro, avec ta raison : mineur (`0.3.0`) s'il y a du « Ajouté », correctif (`0.2.2`) s'il n'y a que du « Corrigé ».

**Attends** que David valide le numéro.

## Étape 2 : l'entretien

Trois questions, **une à la fois**, chacune avec ta reco tirée du CHANGELOG (David répond plus vite à une reco qu'à une question ouverte) :

1. Quel est le thème de cette version, ce qu'un pilote doit en retenir ?
2. Y a-t-il une rupture ou un risque de régression à signaler (un réglage qui change, une manipulation qui n'est plus la même) ?
3. Faut-il mettre en avant une contribution ou un point précis ?

## Étape 3 : les notes de version

1. Écris le contenu complet de `RELEASE_NOTES.md`, sur le modèle de la version précédente (`git show origin/main:RELEASE_NOTES.md` ; la branche `main` locale n'est pas tenue à jour) :
   - titre exactement `# HOTAS Kneeboard — X.Y.Z` (`release.yml` le contrôle) ;
   - en français d'abord, pour les pilotes, puis la même chose en anglais sous `## 🇬🇧 In English` ;
   - une phrase d'accroche, puis des sections par thème avec un emoji, des puces qui disent ce que le pilote y gagne.
2. Retire le bruit technique (refactors, tests, CI, outillage) : ne garde que ce qui change pour celui qui se sert de l'application.
   Pas de vocabulaire d'implémentation ; un terme de DCS ou d'informatique que les pilotes emploient tel quel reste en anglais.
3. Propose le texte à David.

**Attends** sa validation ou ses corrections.

## Étape 4 : la clôture

Une fois les notes validées :

1. **`RELEASE_NOTES.md`** : le texte validé.
2. **`CHANGELOG.md`** : `## [Unreleased]` devient `## [X.Y.Z] - AAAA-MM-JJ` (date du jour), et une section `## [Unreleased]` **vide** est rouverte au-dessus.
   Sans elle, la PR suivante n'a nulle part où écrire : c'est ainsi que VMCT l'a perdue après sa 6.15.0, et chaque PR s'est mise à inventer son propre numéro.
3. **La version** : `pyproject.toml` et `hotas_kneeboard/__init__.py`, puis `uv lock` pour `uv.lock`.
4. **Les captures**, si l'interface a changé depuis la dernière release : `scripts/doc_screenshots.py`, en français puis `--lang en` (marche à suivre dans `docs/developpement.md`, section des captures).
   Regarde les images changées avant de les garder.
5. **Les vérifications** : `uv run pytest` (`tests/test_changelog.py` compris), `uv run ruff check .`, `uv run --group docs mkdocs build --strict`.

## Étape 5 : les deux PR

1. Crée `chore/RELEASE-X.Y.Z` depuis `develop`, committe (`chore(release): X.Y.Z`), pousse, ouvre la PR vers `develop`, titrée `Release X.Y.Z (develop)`.
2. Comme toute PR : `pr-code-review`, CI verte, puis fusion.
3. Ouvre la PR `develop` → `main`, titrée `Release X.Y.Z`.
   Attends la CI verte, puis **demande le feu vert de David** pour fusionner : c'est la fusion qui publie, et elle ne se reprend pas (un tag et une release publiés).
4. Fusionne avec un commit de fusion : `gh pr merge <n> --merge`.

## Étape 6 : le contrôle

1. Le workflow « Release » sur `main` : il doit avoir construit et publié, pas seulement tourné (`gh run list --workflow release.yml --branch main`, puis `gh run view`).
2. La release : `gh release view vX.Y.Z` doit avoir l'exe `HOTAS-Kneeboard.exe`, et les notes avec le lien vers la documentation de la version.
3. La documentation : `https://veaf.github.io/hotas-kneeboard/X.Y.Z/` répond, et `latest` pointe sur elle.
4. Reviens sur `develop` et fais `git pull`.

Rends compte à David en une ligne par point, avec les liens.
