# Changelog

Ce qui change d'une version à l'autre de HOTAS Kneeboard.
Chaque lot ajoute ses entrées à la fin de `[Unreleased]` ; une release les passe sous son numéro de version.

## [Unreleased]

### Ajouté

- L'éditeur de gabarits reconnaît le hat quand tu appuies dessus (« Vérifier », « Identifier ») : il le lit comme le hat 1, dans ses huit directions.

### Corrigé

- Éditeur de gabarits, « Vérifier » : un bouton ou une direction du hat encore tenu quand l'écoute reprend est de nouveau entendu une fois relâché ; il fallait jusque-là appuyer sur autre chose entre deux appuis.
- Gabarits comparés à la documentation des fabricants (FEAT-TEMPLATE-LIBRARY, #4) :
  - manche WinWing Orion JGRIP-F16 : le gabarit reconnu automatiquement est le dessin avec le module additionnel, qui a toutes les cases (gâchette et crans 1, 2, 3, 41, 42, chapeau 21 à 25, mini-manche 26 à 30, axes RX, RY, RZ) ; chapeau 14 renuméroté comme sur le schéma de WinWing, case pour l'axe Z du socle, noms DCS des variantes MFSSB et ZAXIS (#18) ;
  - HUD F/A-18 WinWing : boutons 65 à 83 et molettes X, Y, Z, SLIDER2, comme dans `WINWING UFC1 + HUD1` ;
  - UFC F/A-18 WinWing : cases des sélecteurs de canal COMM (27 à 32) et des molettes VOL et BRT (RX, RY, RZ) ;
  - PCR WinWing : l'interrupteur LST/NFLR est 13, 14, 15 (il portait deux fois le 15) ; cases des molettes de volume COMM (RX, RY) ;
  - Virpil V.F.X : la gâchette est 1 puis 6 ; le 2 est le poussoir du sélecteur ;
  - Virpil MongoosT-50CM2 : numérotation du modèle publié par Virpil (celle du gabarit était décalée de 4) ;
  - Virpil Control Panel #1 : la case du bouton 22 n'occupe plus toute la page, et le fond du dessin est revenu ;
  - throttle WinWing Orion avec poignées F15EX à gauche et F15 à droite : reconnu sur le dessin « 15E », celui de sa poignée droite (trois interrupteurs à 3 positions 3 à 11), et plus sur le dessin à deux poignées F15EX.

## [0.2.1] - 2026-10-19

### Ajouté

- L'application en anglais : l'interface, les messages et la console suivent la langue du navigateur (de Windows pour la console), ou celle choisie dans les réglages (« Langue de l'interface »), appliquée tout de suite.
  Le français reste la langue des pilotes francophones ; les noms de commande restent ceux que DCS affiche dans sa langue.
- Les mots que l'application écrit sur les pages du kneeboard (« relâché : », la ligne de crédit, la page en liste) et les actions de SRS et VectorXR suivent la langue des commandes : en français quand DCS est en français, en anglais sinon.

### Documentation

- La documentation et le README en anglais, avec des captures de l'interface anglaise ; le site a un sélecteur de langue, et le livre de l'application ouvre la documentation dans la langue de l'interface.
- Des captures d'écran dans le guide d'utilisation et la page de l'éditeur de gabarits : l'écran principal, une page, l'export, les fenêtres Autres logiciels, Liaisons, Commandes DCS et Réglages, l'éditeur.

## [0.2.0] - 2026-10-19

### Ajouté

- Lien vers la documentation de ta version dans la barre du haut et dans la fenêtre des raccourcis.
- Export de tous les modules d'un coup, vers leur kneeboard (Maj+E) ou en un seul PDF (Maj+P), depuis la flèche à côté de chaque bouton d'export : les avions qui ont un périphérique coché, avec une fenêtre de progression qui permet d'arrêter ; un module en échec n'arrête pas les autres.
- Les modules portent le nom de l'écran des commandes de DCS (« AH-64D Pilot » au lieu de `AH-64D_BLK_II_PLT`), dans la liste et en en-tête des pages, triés par ce nom ; le dossier du profil reste affiché dessous.
- Les colonnes des modules et des périphériques se redimensionnent en glissant la ligne qui les sépare ; double-clic pour revenir à la largeur par défaut.
- Retrait de liaisons de DCS depuis l'application (bouton **Liaisons** au-dessus de la page) : boutons, chapeaux et axes d'un périphérique dans un module, avec leur origine (ta config ou défaut du module) ; DCS fermé, sauvegarde avant, fichier réécrit comme DCS l'enregistre, **Annuler** dans la même fenêtre (FEAT-REMOVE-DCS-BINDINGS, #53).
- Fenêtre **Liaisons** : l'origine distingue le défaut prévu pour ce périphérique du défaut générique, ce que DCS donne à tout joystick dont le module n'a pas de profil (la gâchette canon sur le bouton 1 d'un throttle), souvent à retirer ; une liaison du fichier que le module livre pour le périphérique, recopié par DCS dans le tien, n'est plus comptée comme la tienne.
- Fenêtre « Commandes DCS », **Périphériques sans boutons** : tu coches ceux qui n'en ont pas (un palonnier), et les boutons que DCS leur donne depuis le profil de « n'importe quel joystick » sont retirés de tous leurs modules, ou de tous les modules installés ; tes liaisons, celles prévues pour ce périphérique et les axes restent ; aperçu, une sauvegarde, relecture, annulation.

### Corrigé

- Boutons VectorXR manquants : les profils PivotXR (vues rapides, recentrage, activation) n'apparaissaient pas quand le module était enregistré éteint, alors qu'ils servent en vol ; l'étiquette nomme maintenant le profil (« PivotXR snapviews : vue Right MFD »).
- Un gabarit choisi à la main par erreur (le manche Warthog dessiné avec l'image de sa manette des gaz, signalé par un pilote) se voit et se défait : entrée **Automatique** en tête de la liste, qui nomme le gabarit reconnu, pastille « choix manuel » quand le choix diffère de celui-ci, liste plus large et nom complet en infobulle.
- Sécurité : un nom de module ou de périphérique contenant une tabulation ou un retour à la ligne est refusé avant d'aller au moteur, qui aurait pu lire d'autres dossiers et y exécuter des fichiers Lua ; les liaisons d'un périphérique ne se lisent que pour un module configuré, et une requête venue d'un autre site est refusée, lecture comprise.
- « Retrait impossible : command not identified » en retirant les boutons d'un périphérique dans tous les modules installés : une liaison dont l'application ne connaît pas le numéro de commande de DCS (le tir secondaire et la tourelle de Combined Arms, `ground_unit`) faisait tout refuser ; elle est maintenant montrée à part, à retirer dans le jeu, et le reste se retire.

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
