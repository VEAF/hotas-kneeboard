# Changelog

Ce qui change d'une version à l'autre de HOTAS Kneeboard.
Chaque lot ajoute ses entrées à la fin de `[Unreleased]` ; une release les passe sous son numéro de version.

## [Unreleased]

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
