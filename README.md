# HOTAS Kneeboard

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
L'interface est en français ; l'internationalisation viendra plus tard.
