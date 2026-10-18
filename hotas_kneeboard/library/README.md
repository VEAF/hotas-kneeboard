# Gabarits livrés

Chaque dossier est un gabarit : `template.json` et l'image du périphérique.
Le format, la conversion, la vérification et la façon de verser un gabarit sont décrits dans [docs/gabarits.md](../../docs/gabarits.md).

## Crédits et licence

Les gabarits de ce dossier sont convertis depuis ceux de [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams), de Robert Cox (Rexeh) et de ses contributeurs, publiés sous licence GNU General Public License v2.
Les images et les dessins sont les leurs ; la conversion (`scripts/convert_jd_templates.py`) retire seulement les cases que Joystick Diagrams remplit, et note où elles étaient.
Chaque `template.json` nomme son fichier d'origine dans `credits.source`, et les dessins gardent la ligne de crédit de Joystick Diagrams.

Ne modifie pas à la main un dossier converti : change `scripts/jd_templates.json` ou le convertisseur, et convertis de nouveau.
Seule exception, un gabarit corrigé dans l'éditeur et marqué `"maintained": true` dans `jd_templates.json`, que la conversion laisse tel quel.
