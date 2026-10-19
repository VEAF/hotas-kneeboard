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

L'application lit tes fichiers sans les modifier, sauf quand tu lui demandes de changer tes commandes DCS (voir [Commandes DCS](#commandes-dcs)) : elle sauvegarde alors tout avant d'écrire.
Sinon, elle écrit seulement les pages du kneeboard, et ses propres réglages dans `%APPDATA%\HOTAS Kneeboard\`.

## L'écran

Trois colonnes, de gauche à droite.

**Modules.**
Chaque profil de commandes que tu as configuré dans DCS (un avion, un hélicoptère, la couche d'interface…), sous le nom que lui donne l'écran des commandes du jeu (« AH-64D Pilot », « F/A-18C »), dans l'ordre alphabétique.
Sous le nom, le dossier du profil dans `Saved Games\DCS\Config\Input` quand il est différent (`AH-64D_BLK_II_PLT`), et le dossier kneeboard de l'avion ; à droite, le nombre de périphériques exportés sur le nombre de périphériques montrés.
Deux profils du même nom (DCS garde parfois l'ancien dossier d'un module renommé, comme `Mi-24P Pilot` et `Mi-24P_pilot`) sont départagés par leur dossier, entre parenthèses.
Le filtre cherche dans le nom, le dossier et le type d'avion.
Un module que DCS ne trouve pas dans ton installation est marqué « module non installé » : seules tes modifications sont connues, pas ses défauts.

**Périphériques.**
Les périphériques configurés pour ce module.
La case à cocher inclut ou non le périphérique dans les exports ; le glisser-déposer change l'ordre des pages.
« gabarit » : le périphérique a un dessin ; « liste » : il n'en a pas, sa page est une liste de commandes.
L'œil, au survol d'une ligne, cache le périphérique dans tous les modules (voir [Réglages](#réglages)).

**La page.**
La page telle qu'elle sera dans le kneeboard, ajustée à l'espace disponible.
Au-dessus : le gabarit utilisé (trouvé automatiquement, ou choisi à la main dans la liste, et alors mémorisé), le bouton pour le **créer** ou le **modifier** dans l'éditeur, l'affichage des calques.
Un choix à la main vaut pour ce périphérique dans tous les modules ; la première entrée de la liste, **Automatique**, nomme le gabarit reconnu par le nom du périphérique et y revient.
Quand le gabarit choisi à la main n'est pas celui-là (le manche dessiné avec l'image de la manette des gaz), la pastille **choix manuel** le signale : son infobulle nomme le gabarit reconnu, un clic y revient.
En bas à droite, le zoom : page entière, toute la largeur, plus ou moins (ou Ctrl+molette).

La ligne entre deux colonnes se glisse pour élargir ou rétrécir la colonne des modules ou celle des périphériques ; l'application s'en souvient, et un double-clic sur la ligne remet la largeur par défaut.

Dans la barre du haut, le livre ouvre cette documentation, celle de ta version de l'application, dans un nouvel onglet ; la fenêtre des raccourcis (`?`) y mène aussi.

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

## Les boutons des autres logiciels

Un bouton peut servir à autre chose qu'à DCS : l'alternat de SRS, l'overlay de VectorXR, une commande vocale de VoiceAttack.
Ces boutons apparaissent sur les pages, à côté des commandes DCS, chaque logiciel dans sa couleur et avec sa pastille (« SRS », « VXR » pour VectorXR) ; la légende est au bas de la page.
Ils sont sur toutes les pages, même avec « Par calque » : ces logiciels ignorent les modificateurs de DCS.

- **SRS** est lu directement, sans jamais toucher à ses réglages.
  Chaque avion a son profil SRS : celui du module est trouvé par son nom (« F-16 » pour « F-16C_50 », « A-10C » pour « A-10C II »), sinon c'est le profil `default`.
  Le bouton **Autres logiciels**, en haut de la page, permet d'en choisir un autre pour ce module, ou aucun ; le choix est mémorisé.
- **VectorXR** est lu directement aussi, et ses boutons valent pour tous les modules.
  Seul ce qui sert dans DCS compte : un profil désactivé, ou un profil d'un autre jeu, n'apparaît pas.
  Un module de VectorXR enregistré éteint (PivotXR, DepthXR…) garde ses boutons : il se rallume en vol, et ses profils DCS servent quand même.
  L'étiquette nomme le profil quand il y en a plusieurs (« PivotXR snapviews : vue Right MFD »).
- **Un autre logiciel** se saisit à la main, depuis **Autres logiciels** : le nom du logiciel, le bouton (dans la liste, ou en appuyant dessus avec **Identifier**) et ce qu'il fait.
  Les entrées se modifient et se suppriment au même endroit.

Dans les réglages, l'onglet **Autres logiciels** indique le dossier de SRS (trouvé dans le registre Windows, à indiquer s'il ne l'est pas), ce qui a été lu, et permet de cacher un logiciel des pages ou de changer sa couleur.

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

**Tous les modules d'un coup** : la flèche à côté de **Kneeboard**, puis **Tous les modules** (ou Maj+E).
Chaque avion de la liste qui a au moins un périphérique coché reçoit ses pages, comme si tu l'exportais à la main ; les profils qui ne sont pas des avions (Default, UiLayer) sont sautés.
Une fenêtre montre où en est l'export (« Module 7 sur 20 », le nom du module, une barre) ; il faut compter une dizaine de secondes pour une vingtaine de modules.
**Arrêter** s'arrête à la fin du module en cours : les modules déjà écrits le restent, et le message de fin dit combien ne l'ont pas été.
Si un module échoue, les autres continuent, et le message de fin dit lequel et pourquoi.

### En PDF

**PDF** (ou Ctrl+P) télécharge un PDF des mêmes pages, une page A4 par page, à environ 200 points par pouce.
La flèche à côté, **Tous les modules** (ou Maj+P), en fait un seul PDF, `HOTAS - tous les modules.pdf`, module après module dans l'ordre de la liste, avec les mêmes avions que pour le kneeboard ; chaque page porte le nom de son module en en-tête.
La même fenêtre montre la progression ; **Arrêter** n'écrit alors aucun PDF, un PDF d'une partie des modules passerait pour le tout.

## Commandes DCS

Le bouton à curseurs, en haut, ouvre la fenêtre **Commandes DCS** : ce que l'application peut changer dans tes commandes, et les sauvegardes qu'elle fait avant.

- **DCS doit être fermé.**
  Le jeu réécrit ses fichiers de commandes quand tu enregistres dans son écran des commandes : l'application refuse toute modification tant que DCS (ou un serveur dédié) tourne.
- **Avant chaque modification**, tout le dossier `Saved Games\DCS\Config\Input` est sauvegardé dans un zip, dans `%APPDATA%\HOTAS Kneeboard\backups\`.
  Les 20 dernières sauvegardes sont gardées ; **Sauvegarder maintenant** en fait une à la main.
- **Restaurer…** remet tes commandes exactement dans l'état de cette sauvegarde, pour tous les modules : les fichiers apparus depuis sont retirés.
  L'état d'avant la restauration est lui-même sauvegardé d'abord, en tête de liste : une restauration se défait en restaurant celle-là.

### Désactiver un périphérique

La liste **Périphériques désactivés dans DCS** reprend tous les périphériques connus : ceux configurés dans un module, et ceux que DCS a vus lors de ses deux derniers lancements (« vu par DCS récemment », lu dans `Saved Games\DCS\Logs\dcs.log` et `dcs.log.old`).

- L'interrupteur désactive le périphérique comme le bouton « Désactiver » de l'écran des commandes du jeu : DCS l'ignore dans tous les modules, et ses commandes sont gardées pour sa réactivation.
- C'est utile pour un périphérique branché dont DCS n'a pas besoin : une manette Bluetooth, un vJoy.
- Dans la liste des périphériques d'un module, un périphérique désactivé porte la pastille **désactivé**.

### Oublier un périphérique absent

La liste **Périphériques absents** montre les périphériques qui ont des commandes enregistrées, mais que DCS n'a pas vus lors de ses deux derniers lancements : un vJoy désinstallé, un périphérique renommé par une mise à jour de son pilote, un manche revendu.
Elle ne sait pas faire la différence avec un périphérique simplement débranché ces jours-là : c'est à toi de choisir.

- **Oublier…** puis **Oublier** supprime les commandes du périphérique dans tous les modules, après une sauvegarde : une restauration les fait revenir.
- Un périphérique que DCS a vu récemment n'est jamais proposé, et un périphérique désactivé non plus : branché, il pourrait ne pas apparaître dans le journal de DCS.
- Sans journal de DCS, ou si le journal ne nomme aucun périphérique, la liste est vide : lance DCS une fois, périphériques branchés.

### Réparer les modificateurs d'un périphérique renommé

Un modificateur (« Paddle », une palette du manche tenue pour changer de calque) est enregistré avec le nom complet de son périphérique.
Quand une mise à jour du pilote renomme le périphérique (WinWing : « WINWING Orion Joystick Base 2 » devenu « WINCTRL Orion Joystick Base Metal 2 »), DCS ne le reconnaît plus et l'ignore sans rien dire.
Les liaisons qui s'en servent restent affichées, dans le jeu comme ici, mais ne marchent plus en vol.

- La section **Modificateurs** les liste, module par module, avec l'ancien et le nouveau nom ; dans la liste des périphériques et sur la page, la pastille **modificateur inactif** le signale aussi.
- Un périphérique est reconnu par son GUID, le même avant et après le renommage, et par le nom que DCS lui a donné à ses deux derniers lancements (`Saved Games\DCS\Logs\dcs.log`) : branche-le et lance DCS une fois avant de réparer.
  Un périphérique simplement débranché n'est pas signalé.
- **Réparer** donne à ces modificateurs le nom que DCS utilise maintenant, dans tous les modules, après une sauvegarde.
- Quand DCS a ignoré un modificateur, il réécrit le fichier des modificateurs sans lui à l'enregistrement suivant, et le supprime s'il ne reste que les réglages par défaut.
  Si une sauvegarde de l'application a encore ce fichier, le module est proposé avec **Ramener** : le fichier revient avec les noms réparés, seul ce fichier est écrit.
  Si tu as supprimé ce fichier toi-même, laisse-le.

### Retirer les vues du chapeau

Tous les modules mettent les 8 vues lentes (« View Up slow », « View Down Left slow »…) sur le premier chapeau de **chaque** périphérique : le palonnier, l'ICP, les MFD en ont aussi, même si l'écran des commandes du jeu ne les montre pas toujours.
Avec TrackIR ou la VR, elles ne servent à rien et encombrent les pages ; la section **Vues du chapeau** les retire en une fois.

- **Chercher** calcule l'aperçu (quelques secondes) : chaque périphérique concerné, le nombre de vues, les modules (dépliables) et les fichiers qui seront créés.
- **Par défaut**, ne sont cochés que les périphériques sur le chapeau desquels tu n'as rien mis toi-même, dans aucun module : le palonnier, l'ICP, les MFD, une manette dont le chapeau ne sert pas.
  Les autres sont listés grisés, avec ce que tu as mis sur leur chapeau.
- **Tous les périphériques, chapeaux utilisés compris** les rend cochables aussi : seules les 8 vues par défaut partent, tes propres liaisons sur le chapeau restent.
- **Tous les modules installés** étend le retrait aux modules que tu n'as jamais configurés : un fichier de commandes est créé pour chaque module et chaque périphérique concerné.
  Sans l'option, seuls les modules qui ont un dossier dans `Saved Games\DCS\Config\Input` sont touchés.
- Un fichier n'est créé que pour un périphérique que DCS a vu lors de ses deux derniers lancements, sous le nom exact que le jeu lui donne ; un périphérique absent garde ses fichiers existants, traités eux aussi.
- **Retirer…** puis **Retirer** : une seule sauvegarde pour toute l'opération, puis les commandes sont relues et comparées à l'aperçu.
  « Conforme à l'aperçu » veut dire que toutes les vues annoncées sont parties ; sinon, chaque écart est listé.
- Les fichiers sont réécrits comme DCS les enregistre : une entrée devenue sans effet (un réglage par défaut qui a changé depuis une mise à jour du module) disparaît, comme quand tu enregistres dans le jeu.
  Un fichier qui ne garde plus aucune différence avec les réglages par défaut est supprimé, comme le fait DCS : le périphérique n'apparaît alors plus dans ce module de l'application, ce n'est pas une perte.
- Pour revenir en arrière, restaure la sauvegarde « avant le retrait des vues du chapeau » dans la liste des sauvegardes.

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

**Autres logiciels.**
Le dossier de SRS, les logiciels montrés sur les pages et leur couleur : voir [les boutons des autres logiciels](#les-boutons-des-autres-logiciels).

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

**Une liaison avec un modificateur (« Paddle + … ») ne marche pas en vol.**
Le pilote du périphérique l'a peut-être renommé : la page porte alors la pastille « modificateur inactif ». Voir [Réparer les modificateurs d'un périphérique renommé](#réparer-les-modificateurs-dun-périphérique-renommé).

**Les pages n'apparaissent pas dans le kneeboard.**
Relance la mission : DCS lit le dossier kneeboard au chargement.
Vérifie le dossier indiqué dans le message après l'export, et que tu voles bien sur l'avion de ce module.
