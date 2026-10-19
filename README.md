<a id="en"></a>

# HOTAS Kneeboard

> 🇫🇷 [Lire ce document en français](#fr)

Kneeboard pages and printable sheets for DCS World, showing what every button of your HOTAS does, drawn on your own hardware.

HOTAS Kneeboard reads how your devices are set up in DCS, module by module, and draws it on the picture of each device: stick, throttle, rudder pedals, panels.
One click writes the pages into the aircraft's kneeboard; another one makes a PDF to print or to share.

A [VEAF](https://www.veaf.org) project, under the GPL v2 license.

## What it does

- **What DCS really does**: the module's defaults, your changes, the defaults you removed, the commands added by the community (Quaggles' injector), with the names as the game shows them in its language.
  Checked identical to DCS's "MAKE HTML" export on the A-10C II and the F-16C.
- **Readable at a glance**: a two-position switch fits on a single label ("LG Handle - UP / DN"); modifier layers (a "Paddle", say) show in colour in the same label, or on one page per layer.
- **Nothing gets lost**: a command bound to an input that has no box on the drawing is listed under the drawing; a device without a drawing gets a list page.
- **Other programs too**: the buttons SRS (per aircraft) and VectorXR use are read directly and drawn in their colour; those of another program (VoiceAttack, OpenKneeboard…) are entered by hand.
- **To the kneeboard in one click**: the pages land in `Saved Games\DCS\Kneeboard\<aircraft>\` and you find them in flight.
- **PDF** of every page of a module.
- **45 device drawings** taken from [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) (Thrustmaster, WinWing, Virpil, VKB, Saitek, CH…), and an **editor** to draw the missing ones or correct the others.
- **Tidying up the DCS controls** (DCS closed, a backup before every change, undoable): remove a binding from a device, with its origin (yours, the one meant for this hardware, or the one DCS gives "any joystick"), remove at once the hat views or the buttons of rudder pedals in every module, disable or forget a device, repair the modifiers of a renamed device.
- **Handy**: everything works from the keyboard, drag and drop for the order of the pages, choices remembered, useless devices hidden.
- **In English or in French**: the interface follows your browser's language, or the one you choose in the settings.

## Installation

1. Download `HOTAS-Kneeboard.exe` from the [releases](https://github.com/VEAF/hotas-kneeboard/releases).
2. Run it: nothing to install, no Python needed.
   A console window opens (closing it quits the app) and the app opens in your browser.
3. It finds DCS by itself: the install through the Windows registry, `Saved Games\DCS` in your profile.
   Otherwise, enter the folders in the settings (cog wheel).

## In two minutes

1. Choose a module on the left, then a device: the page shows what DCS will do.
2. Untick the devices you do not want in the kneeboard, drag them to change the order of the pages.
3. **Kneeboard** (Ctrl+E) writes the pages; they are in the kneeboard the next time you fly this aircraft.
   The arrow beside it (Shift+E) does it for all your aircraft at once.
4. **PDF** (Ctrl+P) downloads the same pages; Shift+P, every module in a single PDF.

`?` shows every keyboard shortcut.

## Documentation

It is also online, with a menu and a search: <https://veaf.github.io/hotas-kneeboard/en/>.

- [User guide](docs/guide-utilisateur.en.md): the screen, the pages, the exports, the settings, the shortcuts, the usual problems.
- [Template editor](docs/editeur-de-gabarits.en.md): draw a device that has no template, correct a template, check it on the real hardware, share it.
- [Templates](docs/gabarits.en.md): the format, the library, the conversion from Joystick Diagrams, how to add a checked template.
- [Development](docs/developpement.en.md): the architecture, the reading engine, the commands, the tests, the branches and the releases.

## Credits

The device drawings come from [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams), by Robert Cox (Rexeh) and its contributors, under the GPL v2 license; every template keeps its credit, recalled at the bottom of each page.
Reading the bindings reproduces DCS's logic (`Scripts/Input/Data.lua`) and runs with the Lua interpreter shipped with the game.

## License

GNU General Public License v2, see [LICENSE](LICENSE).

---

<a id="fr"></a>

# HOTAS Kneeboard

> 🇬🇧 [Read this document in English](#en)

Des pages de kneeboard et des fiches à imprimer pour DCS World, qui montrent ce que fait chaque bouton de ton HOTAS, dessiné sur ton propre matériel.

HOTAS Kneeboard lit la configuration de tes périphériques dans DCS, module par module, et la dessine sur l'image de chaque périphérique : manche, manette des gaz, palonnier, panneaux.
Un clic écrit les pages dans le kneeboard de l'avion ; un autre en fait un PDF à imprimer ou à partager.

Un projet de la [VEAF](https://www.veaf.org), sous licence GPL v2.

## Ce que ça fait

- **Ce que DCS fait vraiment** : les défauts du module, tes modifications, les défauts que tu as retirés, les commandes ajoutées par la communauté (injecteur de Quaggles), avec les noms tels que le jeu les affiche dans sa langue.
  Vérifié identique à l'export « MAKE HTML » de DCS sur l'A-10C II et le F-16C.
- **Lisible d'un coup d'œil** : un interrupteur à deux positions tient sur une seule étiquette (« LG Handle - UP / DN ») ; les calques de modificateurs (un « Paddle » par exemple) apparaissent en couleur dans la même étiquette, ou sur une page par calque.
- **Rien ne se perd** : une commande liée à une entrée qui n'a pas de case sur le dessin est listée sous le dessin ; un périphérique sans dessin a une page en liste.
- **Les autres logiciels aussi** : les boutons que SRS (par avion) et VectorXR utilisent sont lus directement et dessinés dans leur couleur ; ceux d'un autre logiciel (VoiceAttack, OpenKneeboard…) se saisissent à la main.
- **Vers le kneeboard en un clic** : les pages arrivent dans `Saved Games\DCS\Kneeboard\<avion>\` et tu les retrouves en vol.
- **PDF** de toutes les pages d'un module.
- **45 dessins de périphériques** repris de [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) (Thrustmaster, WinWing, Virpil, VKB, Saitek, CH…), et un **éditeur** pour dessiner ceux qui manquent ou corriger les autres.
- **Le ménage dans les commandes de DCS** (DCS fermé, sauvegarde avant chaque modification, annulable) : retirer une liaison d'un périphérique, avec son origine (la tienne, celle prévue pour ce matériel, ou celle que DCS donne à « n'importe quel joystick »), retirer d'un coup les vues du chapeau ou les boutons d'un palonnier dans tous les modules, désactiver ou oublier un périphérique, réparer les modificateurs d'un périphérique renommé.
- **Pratique** : tout se fait au clavier, glisser-déposer pour l'ordre des pages, choix mémorisés, périphériques inutiles masqués.
- **En français ou en anglais** : l'interface suit la langue de ton navigateur, ou celle que tu choisis dans les réglages.

## Installation

1. Télécharge `HOTAS-Kneeboard.exe` dans les [releases](https://github.com/VEAF/hotas-kneeboard/releases).
2. Lance-le : rien à installer, pas besoin de Python.
   Une fenêtre de console s'ouvre (la fermer quitte l'application) et l'application s'ouvre dans ton navigateur.
3. Elle trouve DCS toute seule : l'installation par le registre de Windows, `Saved Games\DCS` dans ton profil.
   Sinon, indique les dossiers dans les réglages (roue dentée).

## En deux minutes

1. Choisis un module à gauche, puis un périphérique : la page montre ce que DCS fera.
2. Décoche les périphériques que tu ne veux pas dans le kneeboard, glisse-les pour changer l'ordre des pages.
3. **Kneeboard** (Ctrl+E) écrit les pages ; elles sont dans le kneeboard au prochain vol sur cet avion.
   La flèche à côté (Maj+E) le fait pour tous tes avions d'un coup.
4. **PDF** (Ctrl+P) télécharge les mêmes pages ; Maj+P, tous les modules dans un seul PDF.

`?` affiche tous les raccourcis clavier.

## Documentation

Elle est aussi en ligne, avec un menu et une recherche : <https://veaf.github.io/hotas-kneeboard/>.

- [Guide d'utilisation](docs/guide-utilisateur.md) : l'écran, les pages, les exports, les réglages, les raccourcis, les problèmes courants.
- [Éditeur de gabarits](docs/editeur-de-gabarits.md) : dessiner un périphérique qui n'a pas de gabarit, corriger un gabarit, le vérifier sur le vrai matériel, le partager.
- [Gabarits](docs/gabarits.md) : le format, la bibliothèque, la conversion depuis Joystick Diagrams, comment verser un gabarit vérifié.
- [Développement](docs/developpement.md) : l'architecture, le moteur de lecture, les commandes, les tests, les branches et les releases.

## Crédits

Les dessins des périphériques viennent de [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams), de Robert Cox (Rexeh) et de ses contributeurs, sous licence GPL v2 ; chaque gabarit garde son crédit, rappelé au bas de chaque page.
La lecture des liaisons reproduit la logique de DCS (`Scripts/Input/Data.lua`) et s'exécute avec l'interpréteur Lua livré avec le jeu.

## Licence

GNU General Public License v2, voir [LICENSE](LICENSE).
