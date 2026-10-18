# VEAF — hotas-kneeboard

Application locale (serveur Python + interface web, livrée en un `.exe`) qui dessine les liaisons HOTAS de DCS sur l'image de chaque périphérique, et les exporte en pages kneeboard (PNG) et en PDF.
GPL v2, imposée par les gabarits repris de Joystick Diagrams.

## Suivi

PRD = issue [#1](https://github.com/VEAF/hotas-kneeboard/issues/1), un ticket par lot (L1 #2, L2 #3, L3 #4).
Une branche et une PR par lot, qui ferme le ticket du lot.

## Structure

- `hotas_kneeboard/` : le serveur FastAPI.
  - `engine.py` + `lua/effective_bindings.lua` : le moteur, repris de VEAF/joystick-diagrams-dcs-world-plugin. Il exécute le Lua avec l'interpréteur de DCS (`bin/luae.exe`) : défauts du module + diff de l'utilisateur, comme `Scripts/Input/Data.lua`.
  - `pages.py` : regroupement par entrée et par calque de modificateurs, appariement des positions relâchées `_OFF`.
  - `dcs.py` : détection de l'install, de Saved Games et de la langue ; traduction des noms de commande par `l10n/<langue>/LC_MESSAGES/input.mo`, comme le jeu.
  - `templates.py` : format des gabarits (docstring) et bibliothèque : gabarits livrés (`library/`, les 45 convertis, à ne pas éditer à la main) puis ceux de l'utilisateur (`%APPDATA%/HOTAS Kneeboard/templates/`), qui passent devant ; enregistrement, suppression, export et import en un fichier zip.
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
- Construire l'exe : `pwsh packaging/build.ps1` → `dist/HOTAS-Kneeboard.exe`. Une étiquette `vX.Y.Z` le publie en release (`.github/workflows/release.yml`).

## Règles

- Le moteur doit rester identique à l'export MAKE HTML : tout changement de `effective_bindings.lua` ou `pages.py` se vérifie avec `compare_make_html.py`.
- Les noms de commande affichés sont ceux du jeu, traduits ; ne pas comparer ni afficher les noms bruts du Lua.
- L'interface est en français, le code et les commentaires en anglais.
- Les gabarits gardent leur crédit et leur licence (`credits` du JSON, ligne de crédit sur la page).
