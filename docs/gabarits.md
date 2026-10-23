# Gabarits

## Le format

Un gabarit est un dossier qui contient `template.json` et l'image du périphérique (SVG, PNG ou JPG), sans aucune étiquette dessus.

```json
{
  "format": 1,
  "name": "Thrustmaster Warthog - Throttle",
  "devices": ["Throttle - HOTAS Warthog"],
  "image": "background.svg",
  "size": [828, 1169],
  "inputs": {
    "JOY_BTN16": { "box": [330, 28, 90, 30] },
    "JOY_BTN1": { "box": [205, 666, 180, 30], "anchor": [545, 706] },
    "JOY_BTN5": { "box": [10, 10, 80, 20], "more_boxes": [[400, 10, 80, 20]] }
  },
  "credits": { "author": "Joystick Diagrams contributors", "source": "https://github.com/…", "license": "GPL-2.0" },
  "checked": { "by": "David", "date": "2026-10-19" },
  "split_at": [566]
}
```

| Champ | Sens |
|---|---|
| `devices` | Les noms DCS des périphériques qui utilisent ce gabarit, sans le GUID entre accolades ; la correspondance ignore la casse. Vide : le gabarit se choisit à la main. |
| `size` | Le repère de l'image : largeur et hauteur, de 1 à 20 000. |
| `inputs` | Une entrée par nom DCS : `JOY_BTN14`, `JOY_BTN_POV1_U` (hat 1 vers le haut), `JOY_X`, `JOY_RZ`, `JOY_SLIDER1`… |
| `box` | La case de l'étiquette : x, y, largeur, hauteur, dans le repère de l'image. |
| `anchor` | Facultatif : le point du bouton, relié à la case par un trait. |
| `more_boxes` | Facultatif : d'autres cases pour la même entrée, quand le périphérique est dessiné sous plusieurs angles. |
| `checked` | Qui a vérifié la numérotation sur le vrai périphérique, et quand ; `null` sinon. |
| `split_at` | Facultatif : les positions x où le dessin se coupe en plusieurs pages kneeboard. |

Une position relâchée (`JOY_BTN17_OFF`) n'a pas de case à elle : elle s'écrit dans celle de `JOY_BTN17`.

## La bibliothèque

L'application cherche les gabarits à deux endroits :

1. ceux livrés avec elle (`hotas_kneeboard/library/` dans le dépôt) ;
2. les tiens, dans `%APPDATA%\HOTAS Kneeboard\templates\`, faits avec l'éditeur ou importés.

Un gabarit à toi passe devant un gabarit livré du même identifiant (le nom du dossier), et devant lui pour la correspondance automatique d'un périphérique.

## Les gabarits de Joystick Diagrams

Les 45 gabarits livrés sont convertis depuis ceux de [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) (Robert Cox, alias Rexeh, et ses contributeurs, GPL v2).
Ce sont des dessins draw.io exportés en SVG, avec une case par entrée qui contient un jeton (`Button_14`, `POV_1_U`, `AXIS_X`) que Joystick Diagrams remplace par la commande.

`scripts/convert_jd_templates.py` les convertit :

- il retire les cases à jeton de l'image et garde le reste : la photo, les traits de rappel, les annotations, le crédit ;
- il remplace le texte HTML de draw.io par du texte SVG simple, que le navigateur sait dessiner dans un PNG et un PDF ;
- il note la position de chaque case sous le nom DCS de l'entrée, en reconnaissant les différentes graphies des jetons ;
- il prend dans `scripts/jd_templates.json` l'identifiant du gabarit, les noms DCS connus, les corrections de numérotation (le coolie du throttle Warthog passe du hat 2 au hat 1), les lignes de découpe et l'état de vérification.

```bash
uv run python scripts/convert_jd_templates.py <chemin de joystick-diagrams>/templates
```

Il affiche, pour chaque gabarit, le nombre d'entrées trouvées et les jetons qu'il n'a pas reconnus.

**À savoir :**

- les noms DCS ne sont connus que pour 20 gabarits ; les autres se choisissent à la main, une fois, et l'application s'en souvient ;
- les noms WinWing viennent de la liste des périphériques que DCS reconnaît (`Scripts\Input\DefaultAssignments.lua`) et des profils livrés par les modules, anciens noms de firmware compris (`WINWING THROTTLE BASE2 + …`) ; les firmwares récents s'appellent `WINCTRL …`, et ne sont connus que ceux vus sur un vrai PC ;
- un nom partagé par deux gabarits n'est mis sur aucun des deux : le throttle F/A-18 avec ou sans axes, l'UFC et le HUD F/A-18 branchés ensemble (`WINWING UFC1 + HUD1`) ; le T.16000M a le dessin droitier, son réglage d'usine (le dessin gaucher se choisit à la main) ;
- le HUD F/A-18 n'existe que branché sur l'UFC : ses boutons sont les 65 à 83 de `WINWING UFC1 + HUD1`, comme le numérote WinWing ;
- les gabarits Virpil n'ont pas de nom DCS, et n'en auront pas : le nom que Windows donne à un périphérique Virpil est celui du socle (« VPC Stick MT-50CM3 »), pas de la poignée qui est dessus, et le logiciel de configuration de Virpil permet de le changer ; choisis le gabarit de ta poignée à la main ;
- l'Orion JGRIP-F16 a deux dessins : Joystick Diagrams appelle « avec kit vibreur » celui qui montre la poignée avec son module additionnel (mini-manche, chapeau 21 à 25, levier de frein à crans 1, 2, 41, 42 et 3, axes RX, RY et RZ), et « sans kit vibreur » la poignée nue ; les noms DCS sont sur le premier, qui couvre les deux : sans le module, ses cases restent vides ;
- la numérotation des gabarits convertis est celle que Joystick Diagrams a dessinée, pas forcément celle du périphérique : sur le JGRIP-F16, le chapeau 14 était tourné d'un quart de tour par rapport au schéma de WinWing ;
- les gabarits WinWing, Virpil et Thrustmaster ont été comparés à la documentation des fabricants (le logiciel SimAppPro de WinWing et les profils WinWing livrés par les modules de DCS, les modèles « Button Mapping » du support Virpil, les manuels Thrustmaster), et corrigés quand elle les contredisait ; restent sans source : le throttle WinWing T1 Super Taurus, les manches Ursa Minor, le throttle Virpil MT-50 CM2 et la poignée droite F-15E ;
- la numérotation d'un périphérique Virpil est celle du profil chargé par son logiciel de configuration : les gabarits suivent les modèles que Virpil publie ;
- deux gabarits sont marqués vérifiés sur le vrai périphérique : le manche WinWing Orion JGRIP-F16 avec son module additionnel, et le throttle WinWing Orion avec poignées F15EX à gauche et F15 à droite (dessin « 15E »).

## Vérifier un gabarit

Avec le périphérique branché :

1. `uv run python scripts/check_templates.py` liste, pour tes périphériques, les entrées liées dans DCS qui n'ont pas de case sur leur gabarit (les vues génériques que DCS met sur le hat de tout périphérique sont ignorées).
   Sans le périphérique, `--device "Throttle - HOTAS Warthog"` (le nom DCS, sans GUID, option répétable) fait le même contrôle sur les liaisons que DCS lui donne par défaut dans chaque module installé (tes modifications comptent là où tu en as fait), sans ce qu'un module donne à n'importe quel joystick faute de profil pour celui-là (les axes et le chapeau de son `default.lua`) : ça trouve les cases qui manquent, pas les erreurs de numérotation, que seul le vrai périphérique montre.
2. Dans l'application, ouvre la page du périphérique, **Modifier**, puis **Vérifier** : appuie sur chaque bouton, déplace ou ajoute les cases (voir l'[éditeur](editeur-de-gabarits.md#vérifier-la-numérotation-sur-le-périphérique)).
3. Indique ton pseudo, **Marquer vérifié**, enregistre : ta version passe devant celle de la bibliothèque, sur ton PC.

## Verser un gabarit dans la bibliothèque

Pour que tout le monde ait le gabarit vérifié, ou un périphérique que Joystick Diagrams n'a pas dessiné :

1. dans l'éditeur, **Exporter** le gabarit ;
2. dézippe le fichier dans `hotas_kneeboard/library/<identifiant>/` (le même identifiant que le gabarit livré qu'il corrige, ou un nouveau) ;
3. pour un gabarit converti, mets `"maintained": true` sur son entrée de `scripts/jd_templates.json` : la conversion le laissera alors tel quel ;
4. propose-le en PR sur le dépôt (voir [Développement](developpement.md)).
