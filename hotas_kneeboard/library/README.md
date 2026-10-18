# Device templates

Each folder is one device template: `template.json` and the picture of the device (format described in `hotas_kneeboard/templates.py`).

## Credits and license

The templates of this folder are converted from the templates of [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) by Robert Cox (Rexeh) and its contributors, released under the GNU General Public License v2.
The pictures and drawings are theirs; the conversion (`scripts/convert_jd_templates.py`) only removes the text boxes Joystick Diagrams fills in and records where they were.
Each `template.json` names its source file in `credits.source`, and the drawings keep the Joystick Diagrams credit line.

Do not edit a converted folder by hand (a template fixed in the editor becomes "maintained", see below): change `scripts/jd_templates.json` or the converter, and convert again:

```bash
uv run python scripts/convert_jd_templates.py <path to joystick-diagrams>/templates
```

## Checking a template

The device names (`devices`) are filled in only for the devices whose DCS name is known; the others are found by choosing the template by hand in the app, which remembers the choice.

The input numbering of a converted template is as Joystick Diagrams drew it, which is not always the device's: the Orion JGRIP-F16 template has no box for the trigger (button 1) nor for buttons 2 and 21–29.
`checked` in `template.json` is null until someone checks it on the real device; the app then shows "numérotation non vérifiée" on its pages.
So far only the Warthog throttle coolie was fixed (POV 2 → POV 1, a remap in `jd_templates.json`); no template is marked checked yet.

To check one, with the device plugged in:

1. `uv run python scripts/check_templates.py` lists, for your devices, the inputs bound in DCS that have no box on their template.
2. In the app, open the device's page, **Modifier le gabarit**, then **Vérifier** (`V`) and press every button of the device in turn: the box of each one lights up, or the editor asks you to click where it is. Move the boxes that are wrong.
3. Type your nickname, **Marquer vérifié**, and save (`Ctrl+S`): your version goes in front of the bundled one, on your PC, and lists your device's DCS name. (A template made for another device, by its `devices`, is not changed: the editor makes a new template for yours.)
4. To give it to everyone: **Exporter**, unzip the file into `hotas_kneeboard/library/<id>/` (same id), and set `"maintained": true` on its entry in `scripts/jd_templates.json` so that converting again leaves it alone. A device Joystick Diagrams never drew is added the same way, with a new id.
