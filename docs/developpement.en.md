# Development

## Architecture

A local app: a Python server that reads DCS and serves a web interface, all shipped as a single `.exe`.

```
hotas_kneeboard/          FastAPI server (127.0.0.1 only)
  engine.py + lua/        engine reading the bindings
  pages.py                grouping per input and per layer, released positions
  dcs.py                  detection of DCS, of Saved Games, of the language; translation of the commands
  templates.py            format and library of the templates
  kneeboard.py            writing of the PNG pages
  dcs_config.py           changes to the DCS controls: refused while DCS runs, backup and restore, devices disabled or forgotten
  hat_views.py            removal at once of the 8 generic hat views (preview, selection, reading again)
  generic_buttons.py      removal at once of the generic buttons of the devices without buttons (same pattern)
  lua_tables.py + lua/    reading and writing DCS's Lua files, with the game's serializer
  settings.py             settings (%APPDATA%/HOTAS Kneeboard/settings.json)
  i18n.py + locales/      the server's messages in French and in English
  app.py                  HTTP routes
  library/                the shipped templates
web/                      Vue 3 + TypeScript + Vite + PrimeVue + VueUse interface
  src/render/             building the pages as SVG (screen, PNG and PDF start from the same SVG)
  src/editor/             template editor
  src/locales/            the interface's texts in French and in English (src/lib/i18n.ts)
scripts/                  conversion of the templates, comparison with DCS, checking of the templates
packaging/                building the exe (PyInstaller)
```

The pages are built in the browser: the PNG goes through a canvas, the PDF through jsPDF.
The server only writes the PNG files; there is neither Chromium nor Cairo to ship.

The DCS controls files (`Saved Games/DCS/Config/Input`) are only changed by `dcs_config.py`, and always through `guarded_write`.
It refuses while DCS runs, since the game writes these files again when it saves its controls.
Before writing, it zips the whole folder into `%APPDATA%/HOTAS Kneeboard/backups/` (the last 20 zips are kept); a restore replaces the folder with a single rename, after backing up the current state.

A DCS file is read by running it with `luae.exe`, which gives back its value as JSON, and written again with the game's `Scripts/Serializer.lua`, in binary (DCS writes LF line endings).
Read then written again this way, the 88 files of a real `Config/Input` (diffs, `modifiers.lua`, `disabled.lua`) are identical byte for byte.
ED's serializer cannot be redistributed: the test fixture has its own, and `test_lua_tables.py` checks that it writes the same bytes as the real one when `DCS_TEST_LUA` is the `bin/luae.exe` of an install.

## The reading engine

A `Saved Games/DCS/Config/Input/<profile>/joystick/<device>.diff.lua` file only holds the user's changes against the module's defaults.
The real bindings are the defaults (Lua programs of the module) plus this diff, merged by rules that live in `DCS World/Scripts/Input/Data.lua`.

`lua/effective_bindings.lua` reproduces this logic and runs with the Lua 5.1 interpreter shipped with DCS (`bin/luae.exe`): the defaults are run as they are, and the commands' "hashes" are computed exactly as in the game.
It comes from VEAF/joystick-diagrams-dcs-world-plugin, where its rules are documented (the plugin's PRD, VEAF/joystick-diagrams-dcs-world-plugin#1).
Additions specific to this repository:

- the aircraft type of each profile, read in the `make_flyable` calls of the module's `entry.lua`: it is the name of the kneeboard folder (`A-10C II` → `A-10C_2`);
- the name the DCS controls screen gives each profile (`display_name`), the string the `name.lua` of its folder returns ("AH-64D Pilot" for `AH-64D_BLK_II_PLT`); the server translates it like the commands, and tells two profiles with the same name apart by their folder;
- a device without a base profile, or of a module not installed, shows what its diff adds rather than nothing;
- the removal of bindings (`remove` records, key or axis by their last field): the engine then computes the diff of each device concerned again as DCS does when saving (`saveDeviceProfile`), against the module's defaults without the diff shipped with it; a removed axis is written as DCS writes it (`["removed"] = { [1] = { ["key"] = "JOY_RZ" } }`, compared with a diff saved by the game);
- the combos whose key is not an input of the device are left out, as DCS does (`getKeyBelongToDevice`): the C-130J's joystick profile declares keyboard keys;
- the devices asked for by `device` records are computed in the module profiles where they have no diff too (the module's defaults, marked `extra`), and `scope installed` adds every installed module profile: that is what allows creating a diff where there is none;
- each binding the user's diff adds or changes is marked `from_diff`, unless the diff shipped by the module for this device places it too: DCS copies that diff into the user's at the first save, what it places is therefore still the module's; those are marked `from_module_diff`;
- `base_file` says where the defaults come from: the module's profile for this device, or its `default.lua`, the profile of "any joystick" when it has none; with both marks, that is the origin in the Bindings window (`app.binding_origin`: `user`, `device`, `generic`);
- each recomputation gives back the number of bindings actually removed (`removed`); `remove_bindings` does not write a device again where none was.

The 8 hat views (`hat_views.py`) come from `Config/Input/Aircrafts/common_joystick_binding.lua`, included in the defaults of every module: they are recognised by the (hash, key) pair, the same in every module (`dnilp34u214…` for `JOY_BTN_POV1_U`…), never by the name shown.
A device is offered by default if no hat binding (a key holding `POV`) comes from a diff, in any module: a module's defaults on a hat (the turret of `ground_unit`, the Ka-50's Shkval) do not count.
Only the views coming from the defaults are removed; a new diff is only created for a device that `Logs/dcs.log` names, under that name.
After writing, the preview is computed again: a view expected that is still there, or a number removed other than expected, is reported.
Checked on 2026-10-19 on a faithful copy of a real `Saved Games`: 505 views removed over 160 device × module pairs (44 files created among them), reading again without difference, and effective bindings identical before and after apart from these views.

The generic buttons (`generic_buttons.py`) are the key bindings of a device whose base is `default.lua`, neither `from_diff` nor `from_module_diff`, on the devices the user marked as without buttons (`Settings.buttonless_devices`, names without GUID): DCS writes nowhere how many buttons a device has.
The default scope is the modules where the device has a diff; `all_modules` adds every installed module (a diff created where there is none). Preview, single backup, reading again and differences are those of the hat views.
A binding whose hash still names an `iCommand…` symbol (`@`), for lack of a learnt number, cannot be removed: its removal cannot be written as DCS writes it; the preview shows it apart (`unknown`), the bindings API marks it `removable: false`.
Checked on 2026-10-19 on a copy of a real `Saved Games`: rudder pedals, 20 bindings in 9 modules, reading again as previewed, no axis touched; the 5 of `ground_unit` (turret, secondary fire) stay apart.

The recomputation covers keys (combos added, removed) and axes (plus the combos whose filter changed, compared as DCS does: default values of `createAxisFilter`, detent values never compared); the force feedback diff is copied from the file, read by `lua_tables`.
A diff entry that no longer matches any command disappears, as when DCS saves; an entry whose command has an unknown `iCommand` number makes the write refused, so as not to lose the binding.
An empty diff is deleted, as DCS does: the device falls back on the module's defaults, and on the diff shipped with it if there is one.
Proven on 2026-10-19 against DCS: 4 views removed by hand in the controls screen (Orion stick, F-16C_50), the same operation made by the app on the same starting state gives the same file byte for byte, and so do the rudder pedals DCS wrote again on the way.
On a faithful copy of a real `Saved Games` (community commands included), writing the 57 diffs again without removing anything leaves the bindings of 55 devices identical; the other 2 only held stale entries, their file is deleted and they fall back on the defaults, with no effect in the game.

The values that go to the engine pass through its standard input, one record per line, fields separated by tabs: `engine._loader_input` refuses any value holding a tab or a line break, which would add records of its own (an `install` elsewhere, whose Lua files the interpreter would run).
The routes that get a module name only accept a configured module, and the server refuses any `/api/` request marked `Sec-Fetch-Site: cross-site`, reads included: a page of another site must not be able to start the engine.

`luae.exe` opens files through the C library, limited to 260 characters on Windows: a diff with a longer path is not read.
The recomputation would take it for a missing diff; `dcs_config.new_diffs` therefore refuses to write when the user's diff exists and the engine did not read it.

The command names shown are translated by `l10n/<language>/LC_MESSAGES/input.mo`, as the game does, English included ("Trim: Nose Up" shows as "Trim Hat - NOSE UP" in the A-10C II).

Any change to the engine or to `pages.py` is checked against the "MAKE HTML" export of the DCS controls screen:

```bash
uv run python scripts/compare_make_html.py "A-10C II" "F-16C_50"
```

The last line is the verdict; the export only covers the devices plugged in when it was made.

## The languages

The interface, the server's messages and the documentation exist in French and in English, the same way as in VEAF-Mission-Creation-Tools.
The command names come from DCS's `l10n` files (the "Commands language" setting) and do not go through this.

- **The texts** are in flat JSON catalogs, one per language: `web/src/locales/<language>.json` for the interface, `hotas_kneeboard/locales/<language>.json` for the server.
  A dotted key (`settings.title`), parameters in braces (`{device}`); a plural is a `<key>.one` / `<key>.other` pair (in French, zero is singular).
  English is the reference: a key missing from another catalog falls back on English, then on the key itself.
- **In the interface**, `t('key', { parameters })` and `tn('key', count)` (`web/src/lib/i18n.ts`); a text holding markup (a `<code>`, a link) goes through the `Tr` component, which puts each named slot where the translation puts `{name}`.
  `lang` is reactive: what reads it is drawn again when the language changes.
- **The interface language** is a setting (`ui_language`: `fr`, `en`, or `null` for the browser's), applied at once; a copy in `localStorage` avoids showing the other language while the settings are read.
- **The server** answers in the language of the request: the interface sends its own in `Accept-Language`, and `i18n.LanguageMiddleware` sets it for the time of the request (a `ContextVar`, seen from synchronous routes too).
  Out of a request (the console of the exe), it is `HOTAS_KNEEBOARD_LANG`, else Windows' display language, else English.
  `t("key", name=value)` in `hotas_kneeboard/i18n.py`.
- **The kneeboard pages** speak the commands' language, not the interface's (`pageLanguage`): in French when DCS is in French, in English otherwise, so that a page does not mix two languages.
  The same holds for the SRS and VectorXR actions drawn on them: the interface asks for `/api/programs` in that language.
- **The tests** check that both catalogs have the same keys and the same parameters, and that every key the code asks for exists (`web/src/lib/__tests__/i18n.test.ts`, `tests/test_i18n.py`).
  The Python tests read the messages in French (`tests/conftest.py`), `test_i18n.py` checks the English ones.

A new text goes into both catalogs, in the same move as the code; a text written straight into a component or an error message is an oversight.

## Commands

Python (with [uv](https://docs.astral.sh/uv/)):

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
DCS_TEST_LUA="C:/jeux/DCS World/bin/luae.exe" uv run pytest
```

Without `DCS_TEST_LUA`, the engine tests look for a Lua 5.1 in the PATH and are skipped if there is none; the CI uses `lua5.1`.

Interface (with npm):

```bash
cd web
npm ci
npx vue-tsc -b && npx vitest run
npm run build
```

`npm run build` writes the interface into `hotas_kneeboard/web/`, ignored by git.

Running for development:

```bash
uv run hotas-kneeboard --no-browser
```

then `npm run dev` in `web/` for the interface reloaded on the fly (the `/api` calls are relayed to the server on port 8642).
`HOTAS_KNEEBOARD_DATA` changes the folder of the user's settings and templates, so as not to touch your own while trying things.

Building the exe:

```bash
pwsh packaging/build.ps1
```

It produces `dist/HOTAS-Kneeboard.exe`.

## The documentation site

The documentation is published on <https://veaf.github.io/hotas-kneeboard/> (the repository's GitHub Pages, `gh-pages` branch) with MkDocs Material and mike, like VEAF-Mission-Creation-Tools'.
The pages are those of `docs/`, except `docs/agents/`, which is meant for the Claude sessions.

It is in French and in English, with the mkdocs-static-i18n plugin, as VMCT does:

- `page.md` is the French page (the default language, at the root of the site), `page.en.md` the English page (under `en/`); a new page is written in both languages and goes into the `nav` of `mkdocs.yml`, written in English, with its translation in `nav_translations`.
- A picture `name.en.png` takes the place of `name.png` on the English site; without it, the English site shows the French picture.
- `README.md` holds the English then the French, from `<a id="fr"></a>`; at build time, `scripts/mkdocs_hooks.py` makes the two home pages of it, `docs/index.en.md` and `docs/index.md` (ignored by git).
- The links of an English page aim at the English pages (`guide-utilisateur.en.md`): that way they work on GitHub as on the site.

Publishing:

- A push to `develop` publishes the "dev" version; as long as no release is out, the site's address opens that one.
- A release (a push to `main`) publishes the version of `pyproject.toml` and marks it "latest", which the site's address opens from then on.
  It is the push to `main` that triggers it, not the `vX.Y.Z` tag: `release.yml` creates the tag with GitHub Actions' token, and an event made with that token starts no other workflow.
- Each PR builds the site with `--strict`: a link to a missing page or an anchor that does not exist makes the CI fail.
  The anchors are GitHub's, accents included (`#vérifier-la-numérotation-sur-le-périphérique`): a link works on both.
  Each language has its own, taken from its headings (`#check-the-numbering-on-the-device` in English); `--strict` catches a link a reworded heading broke.
  A link to a file outside the site (`CHANGELOG.md`, `docs/agents/`) is written as a full GitHub address.

Seeing the site locally, reloaded on each change:

```bash
uv run --group docs mkdocs serve
```

### The screenshots

The pictures of `docs/images/` are taken in the app itself by `scripts/doc_screenshots.py`, which drives the installed Edge with Playwright.
The script only looks: it opens the screens and the windows, runs the previews ("Search"), and clicks on nothing that writes to DCS.
It sets the interface and commands language, and ticks the rudder pedals in "Devices without buttons", which writes the app's settings: it is therefore run on an app started with a throwaway `HOTAS_KNEEBOARD_DATA`, in a first terminal:

```powershell
$env:HOTAS_KNEEBOARD_DATA = "$env:TEMP\hk-shots"; uv run hotas-kneeboard --port 8654 --no-browser
```

then, in a second terminal, the French screenshots, then the English ones:

```powershell
$env:HOTAS_KNEEBOARD_DATA = "$env:TEMP\hk-shots"; uv run --with playwright python scripts/doc_screenshots.py
$env:HOTAS_KNEEBOARD_DATA = "$env:TEMP\hk-shots"; uv run --with playwright python scripts/doc_screenshots.py --lang en
```

- `--lang en` writes `name.en.png` beside each `name.png`, the interface and the commands in English; the script finds the buttons by their text in the interface's catalog, which a reworded label therefore does not break.
- The pictures show the devices of the PC that takes them: the script picks the A-10C II, the WinWing Orion stick and the T-Pendular rudder pedals; elsewhere, change `MODULE`, `STICK` and `RUDDER` at the top of the script.
- The Windows user's name and the throwaway folder are replaced on screen with those of an ordinary pilot (`C:\Users\Pilote`, `%APPDATA%\HOTAS Kneeboard`).
- Screen names as arguments (`ecran`, `editeur`…) retake only those.
- The screenshots are retaken when the interface changes, at the latest in the release PR: look at each picture again before committing it.

## Lots, tickets, branches and releases

The tracking follows the organisation of VEAF-Mission-Creation-Tools, with GitHub issues in place of the `.backlog/` files; the details are in [`docs/agents/issue-tracker.md`](https://github.com/VEAF/hotas-kneeboard/blob/develop/docs/agents/issue-tracker.md).

- The product's PRD is [#1](https://github.com/VEAF/hotas-kneeboard/issues/1); its lots are its sub-issues.
- A lot is an issue labelled `lot`, titled `<LOT-ID> — …`, its PRD in the body; its tickets are its sub-issues, labelled `ticket`, cut with `/to-tickets` before the code.
- The status is a label: ⬜ ready · 🔄 in-progress · 🧑 waiting-human · ⏸ paused; closed = ✅ done or 🚫 won't fix ([details](https://github.com/VEAF/hotas-kneeboard/blob/develop/docs/agents/triage-labels.md)).
- `develop` is the default branch and gets the work, `main` only gets releases.
- A lot is a `feature/`, `fix/` or `chore/<LOT-ID>` branch made from `develop`, and a single PR to `develop`, which closes its tickets and the lot.
  Each lot adds its entries at the end of `[Unreleased]` in [`CHANGELOG.md`](https://github.com/VEAF/hotas-kneeboard/blob/develop/CHANGELOG.md), without touching the version.
- A release is prepared with Claude Code's `/release` command ([`.claude/commands/release.md`](https://github.com/VEAF/hotas-kneeboard/blob/develop/.claude/commands/release.md)), which goes through its steps.
  It takes two PRs: `chore/RELEASE-X.Y.Z` to `develop`, which raises the version in `pyproject.toml`, `hotas_kneeboard/__init__.py` and `uv.lock` and moves `[Unreleased]` under that number, re-opening an empty section; then `develop` to `main`, merged with a merge commit.
  `tests/test_changelog.py` checks that `[Unreleased]` exists and comes first, that the version has its entry in the changelog and that the three files agree.
  On the merge into `main`, the CI builds the exe on Windows and publishes the `vX.Y.Z` release; a merge without a version change publishes nothing.
  If the interface changed since the previous release, the PR also retakes the [screenshots](#the-screenshots).
  Its notes are [`RELEASE_NOTES.md`](https://github.com/VEAF/hotas-kneeboard/blob/develop/RELEASE_NOTES.md), rewritten at each release as for VMCT: in French then English, for the pilots (what changes for them, not the plumbing), the title ending with the version number; the CI refuses to publish if the title does not carry the version, and adds under the title the link to the documentation of that version.
- The CI (Python and interface tests) runs on each PR and on each push to `develop` and `main`.

## Repository rules

- The interface, the server's messages and the documentation are in French and in English (see [The languages](#the-languages)); the code and its comments in English.
- The command names shown are the game's, translated; never show the raw names of the Lua files.
- The templates keep their credit and their license.
- The server only accepts the `127.0.0.1` and `localhost` hosts, and refuses writes coming from another site.
