# HOTAS Kneeboard — 0.3.0

**Des gabarits sur lesquels on peut compter.**
Huit gabarits WinWing et Virpil ont été repris d'après la documentation des fabricants, et deux vérifiés bouton par bouton sur le vrai matériel : les cases tombent sur les bons boutons.

---

## 🎯 Les gabarits corrigés

- **Manche WinWing Orion JGRIP-F16** : le gabarit reconnu automatiquement est maintenant le dessin avec le module additionnel, qui a toutes les cases (gâchette et ses crans, chapeau 21 à 25, mini-manche 26 à 30, axes RX, RY, RZ).
  Le chapeau 14 est numéroté comme sur le schéma de WinWing, et l'axe Z du socle a sa case.
  Vérifié sur le vrai manche.
- **Throttle WinWing Orion, poignée F15EX à gauche et F15 à droite** : reconnu sur le dessin de sa poignée droite (les trois interrupteurs à 3 positions), et plus sur celui à deux poignées F15EX.
  Vérifié sur le vrai throttle.
- **HUD F/A-18 WinWing** : boutons 65 à 83 et les quatre molettes.
- **UFC F/A-18 WinWing** : les sélecteurs de canal COMM et les molettes VOL et BRT ont leur case.
- **PCR WinWing** : l'interrupteur LST/NFLR est 13, 14, 15 (il portait deux fois le 15), et les molettes de volume COMM ont leur case.
- **Virpil V.F.X** : la gâchette est 1 puis 6 ; le 2 est le poussoir du sélecteur.
- **Virpil MongoosT-50CM2** : la numérotation est celle du modèle publié par Virpil ; celle du gabarit était décalée de 4.
- **Virpil Control Panel #1** : la case du bouton 22 ne recouvre plus toute la page, et le fond du dessin est revenu.

---

## ⚠️ Ce que tu as à faire

Si tu as un **JGRIP-F16**, un **throttle Orion F15EX/F15** ou un **MongoosT-50CM2**, réexporte tes pages kneeboard : le dessin ou la numérotation ont changé, et les pages déjà dans DCS sont celles de l'ancien gabarit.
Pour tous les autres périphériques, rien ne change.

Un gabarit te semble faux ? Signale-le sur <https://github.com/VEAF/hotas-kneeboard/issues> ou sur le Discord VEAF, avec le nom du périphérique : chaque signalement rend la bibliothèque plus juste pour tout le monde.

---

## 🛠️ L'éditeur de gabarits

- **Il entend le hat** : dans « Vérifier » et « Identifier », un appui sur le hat est reconnu comme le hat 1, dans ses huit directions.
- **« Vérifier » n'a plus besoin d'un appui intermédiaire** : un bouton encore tenu quand l'écoute reprend est entendu une fois relâché, et le hat passé d'une direction à l'autre sans revenir au centre est entendu.

---

## 🇬🇧 In English

**Templates you can rely on.**
Eight WinWing and Virpil templates were reworked from the manufacturers' documentation, and two were checked button by button on the real hardware: the boxes land on the right buttons.

**Documentation**: https://veaf.github.io/hotas-kneeboard/0.3.0/en/

### 🎯 Fixed templates

- **WinWing Orion JGRIP-F16 stick**: the automatically recognised template is now the drawing with the add-on module, which has every box (trigger and its detents, hat 21 to 25, mini-stick 26 to 30, RX, RY, RZ axes).
  Hat 14 is numbered as on WinWing's diagram, and the base's Z axis has its box.
  Checked on the real stick.
- **WinWing Orion throttle, F15EX grip on the left and F15 on the right**: recognised on the drawing of its right grip (the three 3-position switches), no longer on the one with two F15EX grips.
  Checked on the real throttle.
- **WinWing F/A-18 HUD**: buttons 65 to 83 and the four knobs.
- **WinWing F/A-18 UFC**: the COMM channel selectors and the VOL and BRT knobs have their box.
- **WinWing PCR**: the LST/NFLR switch is 13, 14, 15 (it carried 15 twice), and the COMM volume knobs have their box.
- **Virpil V.F.X**: the trigger is 1 then 6; 2 is the selector's push.
- **Virpil MongoosT-50CM2**: the numbering is that of the model Virpil publishes; the template's was off by 4.
- **Virpil Control Panel #1**: button 22's box no longer covers the whole page, and the drawing's background is back.

### ⚠️ What you have to do

If you have a **JGRIP-F16**, an **Orion F15EX/F15 throttle** or a **MongoosT-50CM2**, export your kneeboard pages again: the drawing or the numbering changed, and the pages already in DCS are those of the old template.
For every other device, nothing changes.

A template looks wrong? Report it on <https://github.com/VEAF/hotas-kneeboard/issues> or on the VEAF Discord, with the device's name: every report makes the library more accurate for everyone.

### 🛠️ The template editor

- **It hears the hat**: in "Check" and "Identify", a press on the hat is recognised as hat 1, in its eight directions.
- **"Check" no longer needs a press in between**: a button still held when listening resumes is heard once released, and the hat moved from one direction to another without going back to the centre is heard.
