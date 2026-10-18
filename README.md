# HOTAS Kneeboard

Generate DCS World kneeboard pages and printable sheets of your HOTAS bindings, drawn on your actual devices.

HOTAS Kneeboard reads what each button of each of your devices does in each DCS module — the module's defaults, your changes, removed defaults gone, community keybinds included — and draws it on a picture of the device.
One click writes the pages into the DCS kneeboard of the aircraft; another makes a PDF to print or share.

## Use it

1. Download `HOTAS-Kneeboard.exe` from the [releases](https://github.com/VEAF/hotas-kneeboard/releases) and run it. Nothing to install: a console opens (close it to quit) and the app opens in your browser.
2. It finds DCS by itself (the install from the Windows registry, `Saved Games\DCS` from your profile). If not, set the folders in the settings (gear icon).
3. Pick a module, then a device: the page shows what DCS will do. Untick the devices you do not want, drag them to change the page order.
4. **Export to the kneeboard** (Ctrl+E) writes the pages into `Saved Games\DCS\Kneeboard\<aircraft>\`; they are in the kneeboard the next time you fly that aircraft. **PDF** (Ctrl+P) downloads the same pages.

Press `?` in the app for every keyboard shortcut.

### What a page shows

- A two-position switch shows both positions on one label: "LG Handle - UP / DN".
- Modifier layers (e.g. a "Paddle" modifier) show as a coloured tag in the label, or one page per layer ("Calques" switch).
- Bindings whose input has no box on the drawing are listed under it, so nothing is lost.
- A device without template gets a list page. You can also pick a template by hand for a device: the choice is remembered.
- Command names are those the game shows, in its language.
- A drawing too wide for one page is cut in two portrait pages where its template says (`split_at`): the WinWing Orion throttles are, between the base and the handles; in the editor, "Découper en deux pages" places the line for any template. Cutting can be turned off in the settings. On screen the two halves stand side by side when the window is wide enough.

### Settings

The gear icon opens the settings, saved in `%APPDATA%\HOTAS Kneeboard\settings.json`: DCS folders, language of the command names, height of the kneeboard pages, cutting of the drawings that have a cut line.
The **Périphériques** tab lists every device seen in your modules: untick one to hide it everywhere (a vJoy, a device unplugged for good). It then leaves the lists and the exports; the eye on a device's row, or `H`, does the same, and "N cachés : Afficher" at the bottom of the list shows them again.

## Templates

The device pictures come from [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) by Robert Cox (Rexeh) and its contributors (GPL v2), converted to our format (see `hotas_kneeboard/library/README.md`).
### Describe a device yourself

A device with no template, or a template to fix: **Créer un gabarit** / **Modifier le gabarit** on its page (or the pencil icon at the top) opens the editor.

1. Drop a photo or drawing of the device on the window (PNG, JPG, SVG), or start from an existing template.
2. Place each input: drag "＋ Entrée" onto the picture, or press `N` and click where the button is. A marker goes on the button, its label box beside it: drag either one, resize the box by its corner.
3. Pick its DCS input (button, hat direction, axis) in the list, or press `I` then the button on the device: the browser recognises it (Gamepad API; check the number it gives, the list stays the reference).
4. `P` previews the template with a module's real bindings; `Ctrl+S` saves it in your library (`%APPDATA%\HOTAS Kneeboard\templates\`), and the device uses it at once.

Undo / redo (`Ctrl+Z` / `Ctrl+Y`), duplicate on the next button (`Ctrl+D`), nudge with the arrows, zoom with `+ − 0`.
A saved template can be exported as one file and imported on another PC; saving a fixed library template puts your version in front of the bundled one.

### Check a template

A page marked "numérotation non vérifiée" uses a library template nobody checked on the real device yet: a command may land on the wrong box.
Open the editor on it, click **Vérifier** (`V`) and press every button of the device: each box lights up, or the editor asks where the button is.
Then **Marquer vérifié** and save; share the file with VEAF so that everyone gets the checked version (`hotas_kneeboard/library/README.md`).

## Develop

See [CLAUDE.md](CLAUDE.md) for the structure and the commands (Python with `uv`, UI with `npm`).

## License

GNU General Public License v2, see [LICENSE](LICENSE).
