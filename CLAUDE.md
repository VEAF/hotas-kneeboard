# VEAF — hotas-kneeboard

Application locale (serveur Python + interface web, livrée en un `.exe`) qui dessine les liaisons HOTAS de DCS sur l'image de chaque périphérique, et les exporte en pages kneeboard (PNG) et en PDF.
GPL v2, imposée par les gabarits repris de Joystick Diagrams.

## Suivi : lots et tickets dans GitHub, comme VMCT

Même organisation que VEAF-Mission-Creation-Tools (VMCT), avec des tickets GitHub à la place des fichiers de `.backlog/` ; le détail est dans [`docs/agents/issue-tracker.md`](docs/agents/issue-tracker.md) et [`docs/agents/triage-labels.md`](docs/agents/triage-labels.md).

- Le PRD du produit est [#1](https://github.com/VEAF/hotas-kneeboard/issues/1) ; ses lots en sont les sous-tickets (feuille de route et avancement).
- Un **lot** est un ticket étiqueté `lot`, titré `<LOT-ID> — …` (`FEAT-…`, `FIX-…`, `CHORE-…`, `DOC-…`, `INVESTIGATE-…`), son PRD dans le corps, ses conditions de fin en cases à cocher.
- Ses **tickets** sont ses sous-tickets, étiquetés `ticket`, titrés `<LOT-ID> NN — …`, numérotés dans l'ordre des dépendances ; ils se découpent avant d'écrire du code en suivant le skill `to-tickets`.
  Ce skill ne peut pas être appelé par un agent (`disable-model-invocation`) : l'agent lit son `SKILL.md` et en suit la démarche, découpage soumis à David avant publication.
- Le **statut** est une étiquette : ⬜ ready · 🔄 in-progress · 🧑 waiting-human · ⏸ paused. Fermé « completed » = ✅ done, fermé « not planned » = 🚫 won't fix.
  Un changement de statut se fait sur le ticket au moment où il arrive.

## Branches et releases

- `develop` est la branche par défaut et reçoit le travail ; `main` ne reçoit que des releases.
- Un lot = une branche `feature/<LOT-ID>`, `fix/<LOT-ID>` ou `chore/<LOT-ID>` créée depuis `develop`, **une seule PR** vers `develop` pour tout le lot, qui ferme ses tickets et le lot (`Closes #…`).
- Une release = une PR de `develop` vers `main`, qui monte la version dans `pyproject.toml` et `hotas_kneeboard/__init__.py` (les deux doivent être égales) et passe la section `[Unreleased]` de `CHANGELOG.md` sous le numéro de version. À la fusion, `.github/workflows/release.yml` construit l'exe sous Windows et publie la release `vX.Y.Z` ; une fusion sans changement de version ne publie rien.
- La CI (`ci.yml`) tourne sur chaque PR et sur les poussées vers `develop` et `main`.

## Démarche par défaut

Pour chaque demande, dans l'ordre :

0. **Se synchroniser** : `git fetch` puis `git pull --ff-only` sur `develop` avant de lire les tickets ou le code.
1. **Analyser** la demande ; une question ou une analyse sans code s'arrête là. En commençant un ticket, le reformuler en 1 à 3 phrases (ce qu'il est, ce que « fini » veut dire) avant tout outil.
2. **Le lot** : s'il n'existe pas, créer son ticket `lot` (PRD dans le corps, statut ⬜ ready) en sous-ticket de #1, et découper ses tickets en suivant le skill `to-tickets` (voir plus haut).
3. **La branche** depuis `develop` (`feature/`, `fix/` ou `chore/<LOT-ID>`) ; le lot et le ticket en cours passent à 🔄 in-progress.
4. **Coder** : code, tests, documentation de `docs/` touchée par le changement.
5. **Tester** et passer la porte de qualité (commandes ci-dessous) ; tout corriger avant de continuer.
6. **`CHANGELOG.md`** : une entrée claire à la fin de `[Unreleased]` ; ne jamais monter la version hors d'une release.
7. **Si David doit tester à la main** : s'arrêter et attendre son feu vert ; le ticket passe à 🧑 waiting-human.
8. **Committer** (Conventional Commits, en anglais) et pousser ; **ouvrir la PR** vers `develop`.
9. **Relire** la PR avec `pr-code-review`, attendre la CI ; corriger, puis fusionner quand les deux sont propres.
10. **Après la fusion** : revenir sur `develop`, `pull`, cocher les conditions de fin tenues, et le dire à David.

## Documentation

- `README.md` et `docs/` (guide d'utilisation, éditeur de gabarits, gabarits, développement) sont en français ; l'internationalisation de l'interface et de la doc viendra plus tard.
- Un changement visible de l'utilisateur met à jour la page de `docs/` qui en parle, dans le même mouvement.

## Structure

- `hotas_kneeboard/` : le serveur FastAPI.
  - `engine.py` + `lua/effective_bindings.lua` : le moteur, repris de VEAF/joystick-diagrams-dcs-world-plugin. Il exécute le Lua avec l'interpréteur de DCS (`bin/luae.exe`) : défauts du module + diff de l'utilisateur, comme `Scripts/Input/Data.lua`.
  - `pages.py` : regroupement par entrée et par calque de modificateurs, appariement des positions relâchées `_OFF`.
  - `dcs.py` : détection de l'install, de Saved Games et de la langue ; traduction des noms de commande par `l10n/<langue>/LC_MESSAGES/input.mo`, comme le jeu.
  - `templates.py` : format des gabarits (docstring) et bibliothèque : gabarits livrés (`library/`, les 45 convertis, à ne pas éditer à la main) puis ceux de l'utilisateur (`%APPDATA%/HOTAS Kneeboard/templates/`), qui passent devant ; enregistrement, suppression, export et import en un fichier zip.
  - `programs.py` : boutons des autres logiciels, en lecture seule : profils SRS (`<SRS>/Client/<profil>.cfg`, boutons comptés depuis 0, mesuré) et réglages VectorXR (`%LOCALAPPDATA%/VectorXR/config/settings.json`) ; les saisies à la main, le choix du profil SRS et les couleurs sont appliqués par l'interface (`web/src/render/programs.ts`).
  - `dcs_config.py` : modifications des fichiers de commandes de DCS (`Saved Games/DCS/Config/Input`) ; toute écriture passe par `guarded_write`, qui refuse tant que DCS tourne (il réécrit ces fichiers en enregistrant ses commandes) et sauvegarde d'abord tout le dossier en zip dans `%APPDATA%/HOTAS Kneeboard/backups/` (les 20 derniers), restaurable depuis l'interface.
    Il gère aussi `disabled.lua` (périphériques désactivés), avec le nom exact que DCS donne au périphérique dans `Logs/dcs.log`.
  - `lua_tables.py` + `lua/lua_tables.lua` : lecture et écriture des fichiers Lua de DCS ; l'écriture passe par le `Scripts/Serializer.lua` du jeu (`serialize_sorted`, fins de ligne LF), pour écrire octet pour octet ce que DCS écrirait.
    Les tests utilisent une copie de remplacement dans la fixture (`tests/dcs_fixture/DCS World/Scripts/Serializer.lua`, le fichier d'ED n'est pas redistribuable), comparée au vrai quand `DCS_TEST_LUA` pointe dans une install.
  - `kneeboard.py` : écriture des PNG dans `Saved Games/DCS/Kneeboard/<type d'unité>/`, fichiers `HOTAS - <profil> - <nn> <titre>.png` ; un export ne remplace que les pages du même profil (deux postes d'un avion partagent le dossier).
  - `app.py` : n'accepte que les hôtes `127.0.0.1`/`localhost` et refuse les écritures d'une autre origine (DNS rebinding).
- `web/` : l'interface Vue 3 + TypeScript + Vite + PrimeVue + VueUse. `src/render/` construit les pages en SVG (affichage, PNG et PDF partent du même SVG). `src/editor/` : l'éditeur de gabarit (état et historique annuler/rétablir dans `state.ts`, écoute des manettes dans `gamepad.ts`). `npm run build` écrit dans `hotas_kneeboard/web/` (ignoré par git).
- `scripts/convert_jd_templates.py` + `jd_templates.json` : conversion des SVG draw.io de Joystick Diagrams. `scripts/compare_make_html.py` : comparaison des pages avec l'export MAKE HTML de DCS.
- `packaging/` : `.exe` PyInstaller (`build.ps1`).

## Commandes

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
DCS_TEST_LUA="C:/jeux/DCS World/bin/luae.exe" uv run pytest
```

Sans `DCS_TEST_LUA`, les tests du moteur cherchent un Lua 5.1 dans le PATH et sont sautés s'il n'y en a pas ; la CI utilise `lua5.1`.

```bash
cd web && npm ci && npx vue-tsc -b && npx vitest run && npm run build
```

- Lancer en développement : `uv run hotas-kneeboard` (port 8642), et `npm run dev` dans `web/` pour l'interface à chaud (proxy `/api`).
- Vérifier les gabarits contre les liaisons réelles : `uv run python scripts/check_templates.py` (entrées liées sans case). La marche à suivre pour vérifier un gabarit sur le périphérique et le verser dans la bibliothèque est dans `hotas_kneeboard/library/README.md`.
- Vérifier contre DCS : cliquer MAKE HTML dans les commandes du jeu, puis `uv run python scripts/compare_make_html.py "A-10C II" "F-16C_50"` ; la dernière ligne est le verdict.
- Reconvertir les gabarits : `uv run python scripts/convert_jd_templates.py <joystick-diagrams>/templates`.
- Construire l'exe : `pwsh packaging/build.ps1` → `dist/HOTAS-Kneeboard.exe`. La publication se fait par la fusion d'une release dans `main` (ci-dessus).

## Agent skills

### Issue tracker

Les lots, PRD et tickets sont des tickets GitHub de `VEAF/hotas-kneeboard` : un lot = un ticket `lot` avec son PRD, ses tickets = ses sous-tickets `ticket`. Voir `docs/agents/issue-tracker.md`.

### Triage labels

Une seule étiquette de statut (⬜ ready · 🔄 in-progress · 🧑 waiting-human · ⏸ paused ; fermé = ✅ done ou 🚫 won't fix), rapportée aux rôles de tri de Matt dans `docs/agents/triage-labels.md`.

## Règles

- Le moteur doit rester identique à l'export MAKE HTML : tout changement de `effective_bindings.lua` ou `pages.py` se vérifie avec `compare_make_html.py`.
- Les noms de commande affichés sont ceux du jeu, traduits ; ne pas comparer ni afficher les noms bruts du Lua.
- L'interface est en français, le code et les commentaires en anglais.
- Les gabarits gardent leur crédit et leur licence (`credits` du JSON, ligne de crédit sur la page).
