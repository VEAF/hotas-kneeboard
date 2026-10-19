# Développement

## Architecture

Une application locale : un serveur Python qui lit DCS et sert une interface web, le tout livré en un seul `.exe`.

```
hotas_kneeboard/          serveur FastAPI (127.0.0.1 seulement)
  engine.py + lua/        moteur de lecture des liaisons
  pages.py                regroupement par entrée et par calque, positions relâchées
  dcs.py                  détection de DCS, de Saved Games, de la langue ; traduction des commandes
  templates.py            format et bibliothèque des gabarits
  kneeboard.py            écriture des pages PNG
  dcs_config.py           modifications des commandes de DCS : refus si DCS tourne, sauvegarde et restauration, périphériques désactivés ou oubliés
  lua_tables.py + lua/    lecture et écriture des fichiers Lua de DCS, avec le sérialiseur du jeu
  settings.py             réglages (%APPDATA%/HOTAS Kneeboard/settings.json)
  app.py                  routes HTTP
  library/                les gabarits livrés
web/                      interface Vue 3 + TypeScript + Vite + PrimeVue + VueUse
  src/render/             construction des pages en SVG (écran, PNG et PDF partent du même SVG)
  src/editor/             éditeur de gabarits
scripts/                  conversion des gabarits, comparaison avec DCS, vérification des gabarits
packaging/                construction de l'exe (PyInstaller)
```

Les pages sont construites dans le navigateur : le PNG passe par un canvas, le PDF par jsPDF.
Le serveur n'écrit que les fichiers PNG ; il n'y a ni Chromium ni Cairo à livrer.

Les fichiers de commandes de DCS (`Saved Games/DCS/Config/Input`) ne sont modifiés que par `dcs_config.py`, et toujours par `guarded_write`.
Elle refuse tant que DCS tourne, car le jeu réécrit ces fichiers quand il enregistre ses commandes.
Avant d'écrire, elle zippe tout le dossier dans `%APPDATA%/HOTAS Kneeboard/backups/` (les 20 derniers zips sont gardés) ; une restauration remplace le dossier en un seul renommage, après avoir sauvegardé l'état courant.

Un fichier de DCS est lu en l'exécutant avec `luae.exe`, qui rend sa valeur en JSON, et réécrit avec le `Scripts/Serializer.lua` du jeu, en binaire (DCS écrit des fins de ligne LF).
Relus puis réécrits ainsi, les 88 fichiers d'un vrai `Config/Input` (diffs, `modifiers.lua`, `disabled.lua`) sont identiques octet pour octet.
Le sérialiseur d'ED n'est pas redistribuable : la fixture de test a le sien, et `test_lua_tables.py` vérifie qu'il écrit les mêmes octets que le vrai quand `DCS_TEST_LUA` est le `bin/luae.exe` d'une install.

## Le moteur de lecture

Un fichier `Saved Games/DCS/Config/Input/<profil>/joystick/<périphérique>.diff.lua` ne contient que les modifications de l'utilisateur par rapport aux défauts du module.
Les liaisons réelles sont les défauts (des programmes Lua du module) plus ce diff, fusionnés selon des règles qui vivent dans `DCS World/Scripts/Input/Data.lua`.

`lua/effective_bindings.lua` reproduit cette logique et s'exécute avec l'interpréteur Lua 5.1 livré avec DCS (`bin/luae.exe`) : les défauts sont exécutés tels quels, et les « hash » des commandes sont calculés exactement comme dans le jeu.
Il vient de VEAF/joystick-diagrams-dcs-world-plugin, où ses règles sont documentées (PRD du plugin, VEAF/joystick-diagrams-dcs-world-plugin#1).
Ajouts propres à ce dépôt :

- le type d'avion de chaque profil, lu dans les appels `make_flyable` du `entry.lua` du module : c'est le nom du dossier kneeboard (`A-10C II` → `A-10C_2`) ;
- un périphérique sans profil de base, ou d'un module non installé, montre ce que son diff ajoute plutôt que rien.

Les noms de commande affichés sont traduits par `l10n/<langue>/LC_MESSAGES/input.mo`, comme le jeu le fait, anglais compris (« Trim: Nose Up » s'affiche « Trim Hat - NOSE UP » dans l'A-10C II).

Tout changement du moteur ou de `pages.py` se vérifie contre l'export « MAKE HTML » de l'écran des commandes de DCS :

```bash
uv run python scripts/compare_make_html.py "A-10C II" "F-16C_50"
```

La dernière ligne est le verdict ; l'export ne couvre que les périphériques branchés au moment où il a été fait.

## Commandes

Python (avec [uv](https://docs.astral.sh/uv/)) :

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
DCS_TEST_LUA="C:/jeux/DCS World/bin/luae.exe" uv run pytest
```

Sans `DCS_TEST_LUA`, les tests du moteur cherchent un Lua 5.1 dans le PATH et sont sautés s'il n'y en a pas ; la CI utilise `lua5.1`.

Interface (avec npm) :

```bash
cd web
npm ci
npx vue-tsc -b && npx vitest run
npm run build
```

`npm run build` écrit l'interface dans `hotas_kneeboard/web/`, ignoré par git.

Lancer en développement :

```bash
uv run hotas-kneeboard --no-browser
```

puis `npm run dev` dans `web/` pour l'interface rechargée à chaud (les appels `/api` sont relayés au serveur sur le port 8642).
`HOTAS_KNEEBOARD_DATA` change le dossier des réglages et des gabarits de l'utilisateur, pour ne pas toucher aux siens pendant les essais.

Construire l'exe :

```bash
pwsh packaging/build.ps1
```

Il produit `dist/HOTAS-Kneeboard.exe`.

## Lots, tickets, branches et releases

Le suivi suit l'organisation de VEAF-Mission-Creation-Tools, avec des tickets GitHub à la place des fichiers de `.backlog/` ; le détail est dans [`docs/agents/issue-tracker.md`](agents/issue-tracker.md).

- Le PRD du produit est [#1](https://github.com/VEAF/hotas-kneeboard/issues/1) ; ses lots en sont les sous-tickets.
- Un lot est un ticket étiqueté `lot`, titré `<LOT-ID> — …`, son PRD dans le corps ; ses tickets sont ses sous-tickets, étiquetés `ticket`, découpés avec `/to-tickets` avant le code.
- Le statut est une étiquette : ⬜ ready · 🔄 in-progress · 🧑 waiting-human · ⏸ paused ; fermé = ✅ done ou 🚫 won't fix ([détail](agents/triage-labels.md)).
- `develop` est la branche par défaut et reçoit le travail, `main` ne reçoit que des releases.
- Un lot, c'est une branche `feature/`, `fix/` ou `chore/<LOT-ID>` créée depuis `develop`, et une seule PR vers `develop`, qui ferme ses tickets et le lot.
  Chaque lot ajoute ses entrées à la fin de `[Unreleased]` dans [`CHANGELOG.md`](../CHANGELOG.md), sans toucher à la version.
- Une release, c'est une PR de `develop` vers `main` qui monte la version dans `pyproject.toml` et `hotas_kneeboard/__init__.py` (les deux doivent être égales) et passe `[Unreleased]` sous ce numéro.
  À la fusion, la CI construit l'exe sous Windows et publie la release `vX.Y.Z` ; une fusion sans changement de version ne publie rien.
- La CI (tests Python et de l'interface) tourne sur chaque PR et sur chaque poussée vers `develop` et `main`.

## Règles du dépôt

- L'interface et la documentation sont en français ; le code et ses commentaires en anglais.
- Les noms de commande affichés sont ceux du jeu, traduits ; ne jamais afficher les noms bruts des fichiers Lua.
- Les gabarits gardent leur crédit et leur licence.
- Le serveur n'accepte que les hôtes `127.0.0.1` et `localhost`, et refuse les écritures venues d'un autre site.
