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
  hat_views.py            retrait en une fois des 8 vues génériques du chapeau (aperçu, sélection, relecture)
  generic_buttons.py      retrait en une fois des boutons génériques des périphériques sans boutons (même schéma)
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
- le nom que l'écran des commandes de DCS donne à chaque profil (`display_name`), la chaîne que rend le `name.lua` de son dossier (« AH-64D Pilot » pour `AH-64D_BLK_II_PLT`) ; le serveur la traduit comme les commandes, et départage deux profils du même nom par leur dossier ;
- un périphérique sans profil de base, ou d'un module non installé, montre ce que son diff ajoute plutôt que rien ;
- le retrait de liaisons (enregistrements `remove`, touche ou axe selon leur dernier champ) : le moteur recalcule alors le diff de chaque périphérique concerné comme DCS le fait en enregistrant (`saveDeviceProfile`), contre les défauts du module sans le diff livré avec lui ; un axe retiré s'écrit comme DCS l'écrit (`["removed"] = { [1] = { ["key"] = "JOY_RZ" } }`, comparé à un diff enregistré par le jeu) ;
- les combinaisons dont la touche n'est pas une entrée du périphérique sont écartées, comme DCS le fait (`getKeyBelongToDevice`) : le profil joystick du C-130J déclare des touches clavier ;
- les périphériques demandés par des enregistrements `device` sont calculés aussi dans les profils de module où ils n'ont pas de diff (défauts du module, marqués `extra`), et `scope installed` ajoute tous les profils de module installés : c'est ce qui permet de créer un diff là où il n'y en a pas ;
- chaque liaison que le diff de l'utilisateur ajoute ou change est marquée `from_diff`, sauf si le diff livré par le module pour ce périphérique la place aussi : DCS recopie ce diff dans celui de l'utilisateur au premier enregistrement, ce qu'il place reste donc le module ; celles-là sont marquées `from_module_diff` ;
- `base_file` dit d'où viennent les défauts : le profil du module pour ce périphérique, ou son `default.lua`, le profil de « n'importe quel joystick » quand il n'en a pas ; avec les deux marques, c'est l'origine de la fenêtre Liaisons (`app.binding_origin` : `user`, `device`, `generic`) ;
- chaque recalcul rend le nombre de liaisons réellement retirées (`removed`) ; `remove_bindings` ne réécrit pas un périphérique où aucune ne l'a été.

Les 8 vues du chapeau (`hat_views.py`) viennent de `Config/Input/Aircrafts/common_joystick_binding.lua`, inclus dans les défauts de chaque module : elles se reconnaissent au couple (hash, touche), identique dans tous les modules (`dnilp34u214…` pour `JOY_BTN_POV1_U`…), jamais au nom affiché.
Un périphérique est proposé par défaut si aucune liaison de chapeau (touche contenant `POV`) ne vient d'un diff, dans aucun module : les défauts d'un module sur un chapeau (la tourelle de `ground_unit`, le Shkval du Ka-50) ne comptent pas.
Seules les vues venues des défauts sont retirées ; un nouveau diff n'est créé que pour un périphérique que `Logs/dcs.log` nomme, sous ce nom.
Après l'écriture, l'aperçu est recalculé : une vue prévue encore présente, ou un nombre retiré différent du prévu, est signalé.
Vérifié le 2026-10-19 sur une copie fidèle d'un vrai `Saved Games` : 505 vues retirées sur 160 couples périphérique × module (dont 44 fichiers créés), relecture sans écart, et des liaisons effectives identiques avant et après à ces vues près.

Les boutons génériques (`generic_buttons.py`) sont les liaisons de touche d'un périphérique dont la base est `default.lua`, ni `from_diff` ni `from_module_diff`, sur les périphériques que l'utilisateur a marqués sans boutons (`Settings.buttonless_devices`, noms sans GUID) : DCS n'écrit nulle part combien de boutons a un périphérique.
La portée par défaut est celle des modules où le périphérique a un diff ; `all_modules` y ajoute tous les modules installés (un diff créé où il n'y en a pas). Aperçu, sauvegarde unique, relecture et écarts sont ceux des vues du chapeau.
Une liaison dont le hash nomme encore un symbole `iCommand…` (`@`), faute de numéro appris, n'est pas retirable : son retrait ne peut pas s'écrire comme DCS ; l'aperçu la montre à part (`unknown`), l'API des liaisons la marque `removable: false`.
Vérifié le 2026-10-19 sur une copie d'un vrai `Saved Games` : palonnier, 20 liaisons dans 9 modules, relecture conforme, aucun axe touché ; les 5 de `ground_unit` (tourelle, tir secondaire) restent à part.

Le recalcul couvre les touches (combinaisons ajoutées, retirées) et les axes (plus les combinaisons dont le filtre a changé, comparé comme DCS : valeurs par défaut de `createAxisFilter`, valeurs de cran jamais comparées) ; le diff de retour de force est recopié depuis le fichier, relu par `lua_tables`.
Une entrée de diff qui ne correspond plus à aucune commande disparaît, comme quand DCS enregistre ; une entrée dont la commande a un numéro `iCommand` inconnu fait refuser l'écriture, pour ne pas perdre la liaison.
Un diff vide est supprimé, comme DCS le fait : le périphérique retombe sur les défauts du module, et sur le diff livré avec lui s'il y en a un.
Prouvé le 2026-10-19 contre DCS : 4 vues retirées à la main dans l'écran des commandes (manche Orion, F-16C_50), la même opération faite par l'appli sur le même état de départ donne le même fichier octet pour octet, et le palonnier que DCS a réécrit au passage aussi.
Sur une copie fidèle d'un vrai `Saved Games` (commandes communautaires comprises), réécrire les 57 diffs sans rien retirer laisse les liaisons de 55 périphériques identiques ; les 2 autres ne contenaient que des entrées périmées, leur fichier est supprimé et ils retombent sur les défauts, sans effet en jeu.

Les valeurs qui vont au moteur passent par son entrée standard, un enregistrement par ligne, champs séparés par des tabulations : `engine._loader_input` refuse toute valeur contenant une tabulation ou un retour à la ligne, qui ajouterait ses propres enregistrements (un `install` ailleurs, dont l'interpréteur exécuterait les fichiers Lua).
Les routes qui reçoivent un nom de module n'acceptent qu'un module configuré, et le serveur refuse toute requête `/api/` marquée `Sec-Fetch-Site: cross-site`, lecture comprise : une page d'un autre site ne doit pas pouvoir lancer le moteur.

`luae.exe` ouvre les fichiers par la bibliothèque C, limitée à 260 caractères sous Windows : un diff au chemin plus long n'est pas lu.
Le recalcul le prendrait pour un diff absent ; `dcs_config.new_diffs` refuse donc d'écrire quand le diff de l'utilisateur existe et que le moteur ne l'a pas lu.

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

## Le site de documentation

La documentation est publiée sur <https://veaf.github.io/hotas-kneeboard/> (GitHub Pages du dépôt, branche `gh-pages`) avec MkDocs Material et mike, comme celle de VEAF-Mission-Creation-Tools.
La page d'accueil est le `README.md`, repris tel quel au moment du build (`scripts/mkdocs_hooks.py`) ; les pages sont celles de `docs/`, sauf `docs/agents/`, qui s'adresse aux sessions Claude.

- Une poussée vers `develop` publie la version « dev » ; tant qu'aucune release n'est sortie, l'adresse du site ouvre celle-là.
- Une release (poussée vers `main`) publie la version de `pyproject.toml` et la marque « latest », que l'adresse du site ouvre ensuite.
  C'est la poussée vers `main` qui déclenche, pas le tag `vX.Y.Z` : `release.yml` crée le tag avec le jeton de GitHub Actions, et un événement fait avec ce jeton ne lance aucun autre workflow.
- Chaque PR construit le site avec `--strict` : un lien vers une page absente ou une ancre qui n'existe pas fait échouer la CI.
  Les ancres sont celles de GitHub, accents compris (`#vérifier-la-numérotation-sur-le-périphérique`) : un lien marche sur les deux.
  Un lien vers un fichier hors du site (`CHANGELOG.md`, `docs/agents/`) s'écrit en adresse GitHub complète.

Voir le site en local, rechargé à chaque modification :

```bash
uv run --group docs mkdocs serve
```

### Les captures d'écran

Les images de `docs/images/` sont prises dans l'application elle-même par `scripts/doc_screenshots.py`, qui pilote l'Edge installé avec Playwright.
Le script ne fait que regarder : il ouvre les écrans et les fenêtres, lance les aperçus (« Chercher »), et ne clique sur rien qui écrive dans DCS.
Il coche quand même le palonnier dans « Périphériques sans boutons », ce qui écrit les réglages de l'application : on le lance donc sur une application démarrée avec un `HOTAS_KNEEBOARD_DATA` jetable, dans un premier terminal :

```powershell
$env:HOTAS_KNEEBOARD_DATA = "$env:TEMP\hk-shots"; uv run hotas-kneeboard --port 8654 --no-browser
```

puis, dans un second terminal :

```powershell
$env:HOTAS_KNEEBOARD_DATA = "$env:TEMP\hk-shots"; uv run --with playwright python scripts/doc_screenshots.py
```

- Les images montrent les périphériques du PC qui les prend : le script choisit l'A-10C II, le manche WinWing Orion et le palonnier T-Pendular ; ailleurs, changer `MODULE`, `STICK` et `RUDDER` en tête du script.
- Le nom de l'utilisateur Windows et le dossier jetable sont remplacés à l'écran par ceux d'un pilote ordinaire (`C:\Users\Pilote`, `%APPDATA%\HOTAS Kneeboard`).
- Des noms d'écran en argument (`ecran`, `editeur`…) ne reprennent que ceux-là.
- Les captures se refont quand l'interface change, au plus tard dans la PR de release : relire chaque image avant de la committer.

## Lots, tickets, branches et releases

Le suivi suit l'organisation de VEAF-Mission-Creation-Tools, avec des tickets GitHub à la place des fichiers de `.backlog/` ; le détail est dans [`docs/agents/issue-tracker.md`](https://github.com/VEAF/hotas-kneeboard/blob/develop/docs/agents/issue-tracker.md).

- Le PRD du produit est [#1](https://github.com/VEAF/hotas-kneeboard/issues/1) ; ses lots en sont les sous-tickets.
- Un lot est un ticket étiqueté `lot`, titré `<LOT-ID> — …`, son PRD dans le corps ; ses tickets sont ses sous-tickets, étiquetés `ticket`, découpés avec `/to-tickets` avant le code.
- Le statut est une étiquette : ⬜ ready · 🔄 in-progress · 🧑 waiting-human · ⏸ paused ; fermé = ✅ done ou 🚫 won't fix ([détail](https://github.com/VEAF/hotas-kneeboard/blob/develop/docs/agents/triage-labels.md)).
- `develop` est la branche par défaut et reçoit le travail, `main` ne reçoit que des releases.
- Un lot, c'est une branche `feature/`, `fix/` ou `chore/<LOT-ID>` créée depuis `develop`, et une seule PR vers `develop`, qui ferme ses tickets et le lot.
  Chaque lot ajoute ses entrées à la fin de `[Unreleased]` dans [`CHANGELOG.md`](https://github.com/VEAF/hotas-kneeboard/blob/develop/CHANGELOG.md), sans toucher à la version.
- Une release, c'est une PR de `develop` vers `main` qui monte la version dans `pyproject.toml` et `hotas_kneeboard/__init__.py` (les deux doivent être égales) et passe `[Unreleased]` sous ce numéro.
  À la fusion, la CI construit l'exe sous Windows et publie la release `vX.Y.Z` ; une fusion sans changement de version ne publie rien.
  Si l'interface a changé depuis la release précédente, la PR refait aussi les [captures d'écran](#les-captures-décran).
  Ses notes sont [`RELEASE_NOTES.md`](https://github.com/VEAF/hotas-kneeboard/blob/develop/RELEASE_NOTES.md), réécrit à chaque release comme pour VMCT : en français, pour les pilotes (ce qui change pour eux, pas la plomberie), le titre finissant par le numéro de version ; la CI refuse de publier si le titre ne porte pas la version, et ajoute sous le titre le lien vers la documentation de cette version.
- La CI (tests Python et de l'interface) tourne sur chaque PR et sur chaque poussée vers `develop` et `main`.

## Règles du dépôt

- L'interface et la documentation sont en français ; le code et ses commentaires en anglais.
- Les noms de commande affichés sont ceux du jeu, traduits ; ne jamais afficher les noms bruts des fichiers Lua.
- Les gabarits gardent leur crédit et leur licence.
- Le serveur n'accepte que les hôtes `127.0.0.1` et `localhost`, et refuse les écritures venues d'un autre site.
