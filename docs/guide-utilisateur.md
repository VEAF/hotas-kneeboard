# Guide d'utilisation

## Premier lancement

Lance `HOTAS-Kneeboard.exe`.
Une console s'ouvre avec l'adresse de l'application (`http://127.0.0.1:8642/`) et ton navigateur s'ouvre dessus.
L'application tourne tant que la console est ouverte : la fermer quitte l'application.
Relancer l'exe alors qu'il tourne déjà rouvre simplement le navigateur sur l'instance en cours.

L'application cherche toute seule :

- l'installation de DCS, dans le registre de Windows (`HKCU\Software\Eagle Dynamics\DCS World`) ;
- le dossier `Saved Games\DCS` (ou `DCS.openbeta`) de ton profil ;
- la langue du jeu, pour afficher les commandes comme DCS les affiche.

La pastille **DCS** en haut est verte quand tout est trouvé ; survole-la pour voir les dossiers.
Si quelque chose manque, un bandeau le dit, avec un accès direct aux réglages.

L'application ne lit que tes fichiers : elle ne modifie jamais ta configuration DCS.
Elle écrit seulement les pages du kneeboard, et ses propres réglages dans `%APPDATA%\HOTAS Kneeboard\`.

## L'écran

Trois colonnes, de gauche à droite.

**Modules.**
Chaque profil de commandes que tu as configuré dans DCS (un avion, un hélicoptère, la couche d'interface…).
Sous le nom, le dossier kneeboard de l'avion ; à droite, le nombre de périphériques exportés sur le nombre de périphériques montrés.
Un module que DCS ne trouve pas dans ton installation est marqué « module non installé » : seules tes modifications sont connues, pas ses défauts.

**Périphériques.**
Les périphériques configurés pour ce module.
La case à cocher inclut ou non le périphérique dans les exports ; le glisser-déposer change l'ordre des pages.
« gabarit » : le périphérique a un dessin ; « liste » : il n'en a pas, sa page est une liste de commandes.
L'œil, au survol d'une ligne, cache le périphérique dans tous les modules (voir [Réglages](#réglages)).

**La page.**
La page telle qu'elle sera dans le kneeboard, ajustée à l'espace disponible.
Au-dessus : le gabarit utilisé (trouvé automatiquement, ou choisi à la main dans la liste, et alors mémorisé), le bouton pour le **créer** ou le **modifier** dans l'éditeur, l'affichage des calques.
En bas à droite, le zoom : page entière, toute la largeur, plus ou moins (ou Ctrl+molette).

## Lire une page

- **Une étiquette par bouton lié**, posée sur la case du dessin.
  Le texte rapetisse pour tenir ; s'il ne tient vraiment pas, la case s'allonge.
- **Les cases en pointillés** sont des entrées du dessin sans commande : des boutons libres.
- **Un interrupteur à deux positions** tient sur une étiquette : « LG Handle - UP / DN ».
  Une position relâchée seule (sans position appuyée) est écrite en italique, précédée de « relâché : ».
- **Les calques de modificateurs.**
  Une commande liée avec un modificateur (le « Paddle » du Warthog par exemple) apparaît dans la même étiquette, en couleur, précédée d'une petite pastille (« P »).
  La légende est au bas de la page (« P = Paddle »).
  Avec « Par calque », chaque calque a sa propre page.
- **Hors gabarit.**
  Une commande liée à une entrée qui n'a pas de case sur le dessin est listée sous le dessin : rien ne se perd.
  C'est souvent le signe d'un gabarit à vérifier (voir l'[éditeur](editeur-de-gabarits.md#vérifier-la-numérotation-sur-le-périphérique)).
- **« numérotation non vérifiée »** : le gabarit vient de la bibliothèque et personne n'a encore vérifié sur le vrai périphérique que chaque bouton tombe sur la bonne case.
- **Les dessins trop larges** pour une page (les throttles WinWing Orion, base et poignées) sont coupés en deux pages, là où le gabarit le prévoit ; à l'écran, les deux moitiés sont côte à côte si la fenêtre est assez large.
- **Un périphérique sans gabarit** a une page en liste : l'entrée (« Bouton 14 », « Hat 1 ↑ », « Axe X »), puis la commande.
  Si la liste est longue, elle continue sur une page suivante.

## Exporter

### Vers le kneeboard

**Kneeboard** (ou Ctrl+E) écrit les pages du module dans `Saved Games\DCS\Kneeboard\<avion>\`, une par périphérique coché (deux pour un dessin coupé, une par calque si tu as choisi « Par calque »).

- Le nom du dossier est le type d'avion de DCS (`A-10C_2` pour le profil « A-10C II »), lu dans le module : c'est celui que le jeu regarde.
- Les pages s'appellent `HOTAS - <module> - 01 <périphérique>.png`, dans l'ordre de la liste.
- Un nouvel export remplace les pages du même module, et seulement celles-là : tes propres pages restent, et les pages d'un autre poste du même appareil aussi (les profils pilote et menu IA de l'AH-64D partagent le dossier `AH-64D_BLK_II`).
- L'export est tout ou rien : si une page ne peut pas être écrite (une image ouverte dans un autre programme par exemple), les pages précédentes restent en place.
- Un profil qui n'est pas un avion (la couche d'interface) n'a pas de kneeboard.

Les pages apparaissent dans le kneeboard de cet avion à la mission suivante.
Leur hauteur se règle dans les réglages (1024 pixels par défaut) ; la largeur suit les proportions du dessin.

### En PDF

**PDF** (ou Ctrl+P) télécharge un PDF des mêmes pages, une page A4 par page, à environ 200 points par pouce.

## Réglages

La roue dentée, en haut, ouvre les réglages.
Ils sont enregistrés dans `%APPDATA%\HOTAS Kneeboard\settings.json` ; le chemin exact est rappelé au bas de la fenêtre.

**Général.**

- Les dossiers de DCS : vides, ils sont trouvés automatiquement.
- La langue des commandes : celle du jeu par défaut, ou une autre langue livrée avec DCS.
- La hauteur des pages kneeboard.
- La découpe en deux pages des dessins qui ont une ligne de découpe.

**Périphériques.**
Tous les périphériques vus dans tes modules, avec le nombre de modules où ils sont configurés.
Décoche un périphérique pour le cacher partout : un vJoy, un périphérique débranché pour de bon, un doublon fantôme.
Un périphérique caché disparaît des listes, des compteurs et des exports, dans tous les modules ; c'est appliqué tout de suite.
« N cachés : Afficher », au bas de la liste des périphériques, les montre de nouveau (grisés) ; l'œil ou la touche `H` les cache ou les montre un par un.

Le reste est mémorisé au fil de l'eau : périphériques exportés, ordre des pages, gabarit choisi à la main, affichage des calques, zoom, thème clair ou sombre.

## Raccourcis clavier

| Touche | Action |
|---|---|
| ↑ ↓ | Périphérique précédent / suivant |
| PgUp PgDn | Module précédent / suivant |
| Alt + ↑ ↓ | Déplacer le périphérique (ordre des pages) |
| Espace | Inclure ou non le périphérique dans l'export |
| H | Cacher ou montrer le périphérique, dans tous les modules |
| L | Calques : sur la même page / une page par calque |
| / | Filtrer les modules |
| Ctrl + E | Exporter le module vers le kneeboard |
| Ctrl + P | PDF du module |
| F5 | Relire les fichiers de DCS et les gabarits |
| Ctrl + molette | Zoomer sur la page |
| ? | La liste des raccourcis |

L'éditeur de gabarits a ses propres raccourcis, listés dans sa colonne de gauche.

## Problèmes courants

**« Installation de DCS introuvable » ou « Dossier Saved Games de DCS introuvable ».**
Indique le dossier dans les réglages : celui qui contient `bin\luae.exe` pour l'installation, celui qui contient `Config\Input` pour Saved Games.

**Une page ne correspond pas à ce que tu as réglé dans DCS.**
Tu as changé tes commandes dans DCS pendant que l'application tournait : F5 relit les fichiers.

**« module non installé » ou « pas de profil de base ».**
DCS n'a pas trouvé les défauts de ce module ou de ce périphérique : la page ne montre que ce que tes modifications ajoutent.

**Un bouton tombe sur la mauvaise case, ou une commande est « hors gabarit ».**
La numérotation du gabarit ne correspond pas à ton périphérique : vérifie-le dans l'[éditeur](editeur-de-gabarits.md#vérifier-la-numérotation-sur-le-périphérique).

**Un périphérique apparaît deux fois, ou porte un nom étrange (« … BOOT »).**
Windows l'a vu une fois sous un autre nom, et DCS a gardé sa configuration ; cache-le dans les réglages.

**Les pages n'apparaissent pas dans le kneeboard.**
Relance la mission : DCS lit le dossier kneeboard au chargement.
Vérifie le dossier indiqué dans le message après l'export, et que tu voles bien sur l'avion de ce module.
