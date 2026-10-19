# HOTAS Kneeboard — 0.2.0

**Cette version fait le ménage dans tes commandes DCS, et exporte tous tes avions d'un coup.**
Les retours des premiers jours ont montré deux choses : on veut ses planchettes pour tous ses avions, pas un par un, et on découvre en les lisant des boutons qui font deux choses sans qu'on le sache.
Le cas d'école : sur l'A-10C II, couper le moteur droit avec le cran OFF de la manette des gaz tirait aussi au canon, parce que DCS met la gâchette sur le bouton 1 de tout joystick qu'il ne connaît pas.
L'application te montre maintenant d'où vient chaque liaison, et te laisse retirer celles qui n'ont rien à faire là.

> ### ⚠️ À savoir avant de modifier tes commandes
>
> Toutes les modifications des commandes de DCS se font **DCS fermé** : le jeu réécrit ces fichiers quand il enregistre ses commandes, et l'application refuse tant qu'il tourne.
> Avant chaque modification, tout ton dossier `Saved Games\DCS\Config\Input` est sauvegardé ; chaque retrait se défait d'un clic (**Annuler**), et les 20 dernières sauvegardes se restaurent depuis la fenêtre **Commandes DCS**.

---

## 🛫 Tous tes avions d'un coup

- **Kneeboard et PDF de tous les modules** : la flèche à côté de **Kneeboard** et de **PDF**, puis **Tous les modules** (ou Maj+E, Maj+P).
  Chaque avion qui a un périphérique coché reçoit ses pages ; le PDF les réunit dans un seul fichier.
- Une fenêtre montre où en est l'export (« Module 7 sur 20 »), et **Arrêter** s'arrête à la fin du module en cours.
- Une vingtaine d'avions s'exportent en une dizaine de secondes.

---

## 🧹 Le ménage dans les commandes de DCS

- **La fenêtre Liaisons**, au-dessus de chaque page : toutes les liaisons du périphérique dans ce module, boutons, chapeaux et axes, avec leur origine.
  - « ta config » : tu l'as posée toi-même ;
  - « défaut pour ce périphérique » : le module l'a prévue pour ce matériel ;
  - « défaut générique » : DCS la donne à n'importe quel joystick qu'il ne connaît pas. C'est là que se cachent la gâchette sur le bouton 1 d'un throttle, ou les gaz sur l'axe Z d'un manche.
  Coche, **Supprimer**, c'est retiré ; **Annuler** remet tout comme avant.
- **Les périphériques sans boutons** (fenêtre **Commandes DCS**) : coche ton palonnier, et les boutons que DCS lui invente (un tir d'arme sur le bouton 2, une direction de roulette sur le 4…) partent de tous les modules d'un coup.
  Ce que tu y as mis toi-même et ses axes restent ; un aperçu avant, une relecture après.

---

## ✈️ Plus lisible

- **Les vrais noms des avions** : « AH-64D Pilot », « F/A-18C », « CH-47F Gunner Station » plutôt que `AH-64D_BLK_II_PLT` ou `FA-18C_hornet`, dans la liste et en tête des pages.
- **Des colonnes à ta largeur** : glisse la ligne entre deux colonnes ; un double-clic revient à la largeur par défaut.
- **La documentation à un clic** : le livre, en haut à droite.

---

## 🔧 Corrigé

- **Les boutons VectorXR manquants** : les vues rapides, le recentrage et l'activation de PivotXR apparaissent, avec le nom du profil (« PivotXR snapviews : vue Right MFD »).
- **Le manche dessiné avec l'image de la manette des gaz** : un gabarit choisi à la main par erreur se voit (pastille « choix manuel ») et se défait (**Automatique** en tête de la liste).
- **La sécurité** : une page web d'un autre site, ouverte dans ton navigateur, ne peut plus faire travailler l'application à ton insu.

---

## 🙏 Merci

À Angrydad (VEAF), pour ses retours dès le premier jour, dont le manche Warthog qui avait l'image de sa manette des gaz.
