# HOTAS Kneeboard — 0.1.0

**Première version : ce que fait chaque bouton de ton HOTAS, dessiné sur ton propre matériel, dans le kneeboard de l'avion.**
Fini de chercher en vol sur quel bouton tu avais mis le TMS, ou de garder une capture de l'écran des commandes sur un deuxième écran.
HOTAS Kneeboard lit ce que DCS fait vraiment de tes périphériques, module par module, et le dessine sur l'image de chacun : manche, manette des gaz, palonnier, panneaux.
Un clic envoie les pages dans le kneeboard de l'avion, un autre en fait un PDF à imprimer ou à partager.

> ### 🚀 Pour démarrer
>
> 1. Télécharge `HOTAS-Kneeboard.exe` en bas de cette page et lance-le : rien à installer, pas besoin de Python.
>    L'exe n'est pas signé : si Windows affiche « Windows a protégé votre ordinateur », clique sur **Informations complémentaires** puis **Exécuter quand même**.
> 2. Une console s'ouvre (la fermer quitte l'application), et l'application s'ouvre dans ton navigateur ; elle trouve DCS toute seule.
> 3. Choisis un module, puis un périphérique : la page montre ce que DCS fera. **Kneeboard** (Ctrl+E) écrit les pages, tu les retrouves au prochain vol sur cet avion.

---

## 🎯 Ce que DCS fait vraiment, pas ce que tu crois avoir réglé

- **Les vraies commandes** : les défauts du module, tes modifications, les défauts que tu as retirés, et les commandes ajoutées par la communauté (injecteur de Quaggles).
  Vérifié identique à l'export « MAKE HTML » de DCS sur l'A-10C II et le F-16C.
- **Les noms du jeu**, traduits comme DCS les affiche dans sa langue.
- **Lisible d'un coup d'œil** : un interrupteur à deux positions tient sur une seule étiquette (« LG Handle - UP / DN »), et un modificateur comme le « Paddle » s'affiche en couleur dans la même étiquette, ou sur une page à lui.
- **Rien ne se perd** : une commande liée à un bouton qui n'a pas de case sur le dessin est listée sous le dessin, et un périphérique sans dessin a une page en liste.

---

## 🖨️ Dans le kneeboard ou sur papier

- **Kneeboard** : les pages arrivent dans `Saved Games\DCS\Kneeboard\<avion>\`, une par périphérique ; les dessins trop larges (les throttles WinWing Orion) sont coupés en deux pages.
- **PDF** de toutes les pages d'un module, une page A4 par page.
- Tu choisis les périphériques à mettre dans le kneeboard et leur ordre, par glisser-déposer ; l'application s'en souvient.

---

## 🕹️ 45 périphériques dessinés, et un éditeur pour les autres

- **45 dessins** repris de Joystick Diagrams : Thrustmaster, WinWing, Virpil, VKB, Saitek, CH…
  Le Warthog est complet (axes, crans OFF des gaz, friction), et 20 périphériques sont reconnus tout seuls ; pour les autres, tu choisis le dessin une fois.
- **Un éditeur** pour dessiner un périphérique qui manque ou corriger un dessin : tu appuies sur le bouton, l'éditeur te dit lequel c'est.
  Le mode **Vérifier** contrôle la numérotation sur ton vrai matériel, et un dessin se partage en un fichier.

---

## 📻 SRS, VectorXR et les autres

- Les boutons que **SRS** (avec le profil de chaque avion) et **VectorXR** utilisent sont lus directement et dessinés dans leur couleur.
- Ceux d'un autre logiciel (VoiceAttack, OpenKneeboard…) se saisissent à la main.

---

## 🧹 Faire le ménage dans les commandes de DCS

La fenêtre **Commandes DCS** corrige ce que l'écran des commandes du jeu ne sait pas faire.
Elle ne touche à rien tant que DCS tourne, et sauvegarde tout ton dossier de commandes avant chaque modification ; les 20 dernières sauvegardes se restaurent en un clic.

- **Retirer en une fois les 8 vues** que DCS met d'office sur le chapeau de chaque périphérique (palonnier, ICP, MFD…), dans tous tes modules.
- **Désactiver un périphérique** dans DCS, ou **oublier** un périphérique que tu n'as plus.
- **Réparer les modificateurs** d'un périphérique que son pilote a renommé : DCS les ignore sans prévenir, et le « Paddle » ne marche plus en vol.

---

## ⚠️ À savoir

- Windows seulement, et l'interface est en français.
- Les dessins viennent de Joystick Diagrams et leur numérotation n'est pas toujours celle du vrai périphérique (celui du manche Orion JGRIP-F16 n'a pas de case pour la gâchette) : si un bouton tombe à côté, le mode **Vérifier** de l'éditeur le corrige.
- Clavier et souris ne sont pas dessinés : joysticks, palonniers et panneaux seulement.

---

## 🙏 Merci

À Angrydad (VEAF), pour l'idée de départ.
À Robert Cox (Rexeh) et aux contributeurs de [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams), dont viennent les dessins des périphériques (GPL v2), et à Quaggles pour son injecteur de commandes.
