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

## Templates

The device pictures come from [Joystick Diagrams](https://github.com/Rexeh/joystick-diagrams) by Robert Cox (Rexeh) and its contributors (GPL v2), converted to our format (see `hotas_kneeboard/library/README.md`).
Your own templates go in `%APPDATA%\HOTAS Kneeboard\templates\<name>\` (`template.json` + picture, format in `hotas_kneeboard/templates.py`); an on-screen editor comes next.

## Develop

See [CLAUDE.md](CLAUDE.md) for the structure and the commands (Python with `uv`, UI with `npm`).

## License

GNU General Public License v2, see [LICENSE](LICENSE).
