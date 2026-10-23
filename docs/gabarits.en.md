# Templates

## The format

A template is a folder that holds `template.json` and the device's picture (SVG, PNG or JPG), without any label on it.

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

| Field | Meaning |
|---|---|
| `devices` | The DCS names of the devices that use this template, without the GUID in braces; the match ignores case. Empty: the template is chosen by hand. |
| `size` | The picture's frame: width and height, from 1 to 20,000. |
| `inputs` | One input per DCS name: `JOY_BTN14`, `JOY_BTN_POV1_U` (hat 1 up), `JOY_X`, `JOY_RZ`, `JOY_SLIDER1`… |
| `box` | The label's box: x, y, width, height, in the picture's frame. |
| `anchor` | Optional: the button's point, linked to the box by a line. |
| `more_boxes` | Optional: other boxes for the same input, when the device is drawn from several angles. |
| `checked` | Who checked the numbering on the real device, and when; `null` otherwise. |
| `split_at` | Optional: the x positions where the drawing is cut into several kneeboard pages. |

A released position (`JOY_BTN17_OFF`) has no box of its own: it is written in the one of `JOY_BTN17`.

## The library

The app looks for templates in two places:

1. those shipped with it (`hotas_kneeboard/library/` in the repository);
2. yours, in `%APPDATA%\HOTAS Kneeboard\templates\`, made with the editor or imported.

A template of yours comes before a shipped template with the same id (the folder's name), and before it for the automatic match of a device.

## The Joystick Diagrams templates

The 45 shipped templates are converted from those of [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) (Robert Cox, alias Rexeh, and its contributors, GPL v2).
They are draw.io drawings exported as SVG, with a box per input holding a token (`Button_14`, `POV_1_U`, `AXIS_X`) that Joystick Diagrams replaces with the command.

`scripts/convert_jd_templates.py` converts them:

- it removes the token boxes from the picture and keeps the rest: the photo, the leader lines, the notes, the credit;
- it replaces draw.io's HTML text with plain SVG text, which the browser can draw into a PNG and a PDF;
- it records the position of each box under the input's DCS name, recognising the different spellings of the tokens;
- it takes from `scripts/jd_templates.json` the template's id, the known DCS names, the numbering corrections (the Warthog throttle's coolie goes from hat 2 to hat 1), the cut lines and the checking state.

```bash
uv run python scripts/convert_jd_templates.py <path of joystick-diagrams>/templates
```

It shows, for each template, the number of inputs found and the tokens it did not recognise.

**Good to know:**

- the DCS names are only known for 20 templates; the others are chosen by hand, once, and the app remembers it;
- the WinWing names come from the list of devices DCS recognises (`Scripts\Input\DefaultAssignments.lua`) and from the profiles shipped by the modules, old firmware names included (`WINWING THROTTLE BASE2 + …`); recent firmwares are named `WINCTRL …`, and only those seen on a real PC are known;
- a name shared by two templates is put on neither: the F/A-18 throttle with or without axes, the F/A-18 UFC and HUD plugged together (`WINWING UFC1 + HUD1`); the T.16000M gets the right-handed drawing, its factory setting (the left-handed one is chosen by hand);
- the F/A-18 HUD only exists plugged into the UFC: its buttons are 65 to 83 of `WINWING UFC1 + HUD1`, as WinWing numbers them;
- the Virpil templates have no DCS name, and will have none: the name Windows gives a Virpil device is the base's ("VPC Stick MT-50CM3"), not the grip's on it, and Virpil's configuration software lets you change it; choose your grip's template by hand;
- the Orion JGRIP-F16 has two drawings: Joystick Diagrams calls "with shaker kit" the one showing the grip with its add-on module (mini-stick, hat 21 to 25, brake lever with detents 1, 2, 41, 42 and 3, axes RX, RY and RZ), and "without shaker kit" the bare grip; the DCS names are on the first one, which covers both: without the module, its boxes stay empty;
- the numbering of the converted templates is the one Joystick Diagrams drew, not necessarily the device's: on the JGRIP-F16, hat 14 was turned a quarter turn from WinWing's diagram;
- the WinWing, Virpil and Thrustmaster templates were compared with the manufacturers' documentation (WinWing's SimAppPro software and the WinWing profiles shipped by the DCS modules, the "Button Mapping" templates of Virpil's support, Thrustmaster's manuals), and fixed where it contradicted them; still without a source: the WinWing T1 Super Taurus throttle, the Ursa Minor sticks, the Virpil MT-50 CM2 throttle and the F-15E right grip;
- a Virpil device's numbering is the one of the profile its configuration software loaded: the templates follow the button mappings Virpil publishes;
- no template is marked checked yet.

## Checking a template

With the device plugged in:

1. `uv run python scripts/check_templates.py` lists, for your devices, the inputs bound in DCS that have no box on their template (the generic views DCS puts on the hat of every device are ignored).
   Without the device, `--device "Throttle - HOTAS Warthog"` (the DCS name, without GUID, repeatable option) makes the same check on the bindings DCS gives it by default in each installed module (your changes count where you made some), without what a module gives any joystick for lack of a profile for that one (the axes and the hat of its `default.lua`): it finds the missing boxes, not the numbering errors, which only the real device shows.
2. In the app, open the device's page, **Edit**, then **Check**: press every button, move or add the boxes (see the [editor](editeur-de-gabarits.en.md#check-the-numbering-on-the-device)).
3. Enter your nickname, **Mark as checked**, save: your version comes before the library's, on your PC.

## Adding a template to the library

For everyone to have the checked template, or a device Joystick Diagrams did not draw:

1. in the editor, **Export** the template;
2. unzip the file into `hotas_kneeboard/library/<id>/` (the same id as the shipped template it corrects, or a new one);
3. for a converted template, put `"maintained": true` on its entry of `scripts/jd_templates.json`: the conversion will then leave it as it is;
4. offer it as a PR on the repository (see [Development](developpement.en.md)).
