# Changelog

Ce qui change d'une version à l'autre de HOTAS Kneeboard.
Chaque lot ajoute ses entrées à la fin de `[Unreleased]` ; une release les passe sous son numéro de version.

## [Unreleased]

### Ajouté

- Lien vers la documentation de ta version dans la barre du haut et dans la fenêtre des raccourcis.

### Corrigé

- Boutons VectorXR manquants : les profils PivotXR (vues rapides, recentrage, activation) n'apparaissaient pas quand le module était enregistré éteint, alors qu'ils servent en vol ; l'étiquette nomme maintenant le profil (« PivotXR snapviews : vue Right MFD »).

## [0.1.0] - 2026-10-19

Première version publiée.

### Ajouté

- Lecture des liaisons réelles de DCS pour chaque module : défauts du module, modifications de l'utilisateur, commandes de la communauté, noms traduits comme dans le jeu ; identique à l'export « MAKE HTML » sur l'A-10C II et le F-16C (FEAT-READ-SEE-EXPORT, #2).
- Pages par périphérique : dessin avec une étiquette par bouton, positions relâchées sur l'étiquette de la position appuyée, calques de modificateurs, commandes sans case listées sous le dessin, page en liste pour un périphérique sans dessin (#2).
- Export des pages vers le kneeboard de l'avion et en PDF ; `.exe` Windows autonome (#2).
- 45 gabarits convertis depuis Joystick Diagrams (#2).
- Éditeur de gabarits : image, placement des entrées au glisser-déposer, identification d'un bouton en appuyant dessus, annuler / rétablir, aperçu, bibliothèque personnelle, partage en un fichier (FEAT-TEMPLATE-EDITOR, #3).
- Vérification de la numérotation d'un gabarit sur le vrai périphérique, statut « vérifié », script de contrôle des gabarits (FEAT-TEMPLATE-LIBRARY, #4).
- Réglages : périphériques cachés dans tous les modules, langue des commandes, hauteur des pages, découpe des dessins trop larges.
- Découpe en deux pages des dessins qui ont une ligne de découpe (les throttles WinWing Orion), placée dans l'éditeur pour les autres ; les deux moitiés côte à côte à l'écran.
- Documentation en français : README, guide d'utilisation, éditeur, gabarits, développement.
- Boutons des autres logiciels sur les pages, chacun dans sa couleur : SRS lu directement avec le profil de chaque avion, VectorXR lu directement, tout autre logiciel saisi à la main ; logiciels montrés et couleurs dans les réglages (FEAT-OTHER-APPS-BINDINGS, #24).
- Fenêtre « Commandes DCS » : toute modification des commandes de DCS est refusée tant que le jeu tourne et précédée d'une sauvegarde de `Saved Games\DCS\Config\Input` ; les 20 dernières sauvegardes sont listées et restaurables (INVESTIGATE-EDIT-DCS-BINDINGS, #30).
- Désactivation et réactivation d'un périphérique dans DCS depuis la fenêtre « Commandes DCS », écrites comme le jeu les écrit ; pastille « désactivé » dans la liste des périphériques (INVESTIGATE-EDIT-DCS-BINDINGS, #33).
- Oubli d'un périphérique que DCS n'a pas vu lors de ses deux derniers lancements (vJoy désinstallé, périphérique renommé) : ses commandes sont supprimées dans tous les modules, après une sauvegarde (INVESTIGATE-EDIT-DCS-BINDINGS, #34).
- Retrait en une fois des 8 vues lentes que DCS met sur le premier chapeau de chaque périphérique (palonnier, ICP, MFD…), depuis la fenêtre « Commandes DCS » : aperçu par périphérique et par module, par défaut les périphériques dont tu n'as pas utilisé le chapeau, options « tous les périphériques » (tes liaisons sur le chapeau restent) et « tous les modules installés » (un fichier créé par module) ; une seule sauvegarde, relecture après l'écriture comparée à l'aperçu (INVESTIGATE-EDIT-DCS-BINDINGS, #32).
- Documentation publiée sur <https://veaf.github.io/hotas-kneeboard/> : version « dev » à chaque modification de `develop`, une version par release ; liens et ancres vérifiés à chaque PR (DOC-PUBLISH, #39).
- Gabarit du throttle Thrustmaster Warthog complété : cases des crans OFF (boutons 29 et 30), du levier de friction et des quatre axes (gaz gauche et droit, slew) ; toutes les entrées que les modules installés lient par défaut ont leur case. Pas encore vérifié sur le vrai périphérique (FEAT-TEMPLATE-LIBRARY, #19).
- Gabarit du manche Thrustmaster Warthog : cases des axes X et Y, sur le même contrôle par les défauts des modules installés (FEAT-TEMPLATE-LIBRARY).
- Reconnaissance automatique de 7 périphériques WinWing de plus (UFC F/A-18, PCR, PTO, PTO 2, throttle F16EX, manche et throttle F/A-18) et des anciens noms de firmware des Orion, d'après la liste des périphériques de DCS ; les gabarits Virpil restent à choisir à la main, le nom Windows ne disant pas quelle poignée est sur le socle (FEAT-TEMPLATE-LIBRARY, #23).
- `check_templates.py --device "<nom DCS>"` contrôle un gabarit sans avoir le périphérique, sur les liaisons que DCS lui donne par défaut dans chaque module installé (#19).

### Corrigé

- Les touches clavier qu'un module déclare dans son profil joystick (le C-130J : « G », « LShift - D »…) n'apparaissent plus sur les pages des joysticks : DCS les écarte aussi ; vérifié identique à MAKE HTML sur le C-130J (INVESTIGATE-EDIT-DCS-BINDINGS, #31).
- Un fichier de commandes dont le chemin dépasse 260 caractères, que l'interpréteur de DCS ne peut pas lire, est signalé sur sa page (« chemin trop long ») au lieu d'afficher les défauts du module sans prévenir (#31).
- Modificateurs perdus quand le pilote d'un périphérique le renomme (même GUID, nouveau nom) : DCS les ignore sans prévenir et leurs liaisons ne marchent plus en vol ; la fenêtre « Commandes DCS » les liste et les répare dans tous les modules, avec le nom que DCS utilise ; elle propose de ramener depuis une sauvegarde le fichier de modificateurs que DCS a supprimé ; pastille « modificateur inactif » sur les périphériques concernés (FIX-RENAMED-DEVICE-MODIFIERS, #37, #38).
