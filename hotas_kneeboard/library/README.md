# Device templates

Each folder is one device template: `template.json` and the picture of the device (format described in `hotas_kneeboard/templates.py`).

## Credits and license

The templates of this folder are converted from the templates of [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) by Robert Cox (Rexeh) and its contributors, released under the GNU General Public License v2.
The pictures and drawings are theirs; the conversion (`scripts/convert_jd_templates.py`) only removes the text boxes Joystick Diagrams fills in and records where they were.
Each `template.json` names its source file in `credits.source`, and the drawings keep the Joystick Diagrams credit line.

Do not edit these folders by hand: change `scripts/jd_templates.json` or the converter, and convert again:

```bash
uv run python scripts/convert_jd_templates.py <path to joystick-diagrams>/templates
```

## To check

The device names (`devices`) are filled in only for the devices whose DCS name is known; the others are found by choosing the template by hand in the app, which remembers the choice.
The input numbering of a converted template is not checked against the real device: the Warthog throttle coolie is remapped from POV 2 to POV 1, the other templates are as Joystick Diagrams drew them (lot L3 checks them).
