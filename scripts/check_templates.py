"""Checks the templates against what DCS really binds on your devices.

For every device configured in Saved Games/DCS/Config/Input, with the template the app gives it
(the automatic match, or the one chosen in the app), lists the inputs that have a binding in at
least one module but no box on the drawing. Such an input is either a numbering error of the
template (the Warthog throttle coolie drawn as hat 2) or a button the drawing
lacks; check it on the device with the editor's "Vérifier" mode.

Hats bound only to DCS's generic view commands ("View Up slow"…) are left out: DCS gives them
to every device, hat or not.

With --device, checks instead the named devices without having them: their bindings are those
DCS gives them by default in every installed module, as if they were plugged in with no diff
(a module where you configured the device keeps your diff). What a module gives any joystick
from its default.lua is left out: it says nothing of the device.

Usage: uv run python scripts/check_templates.py [--install DIR] [--saved-games DIR]
       [--device "Throttle - HOTAS Warthog" ...]
"""

import argparse
import sys
from pathlib import Path

from hotas_kneeboard.dcs import command_translator, detect_language, detect_saved_games_dir
from hotas_kneeboard.engine import detect_dcs_install_dir, list_user_profiles, load_effective_bindings
from hotas_kneeboard.pages import build_page
from hotas_kneeboard.settings import SettingsStore, data_dir
from hotas_kneeboard.templates import BUNDLED_DIR, TemplateLibrary

GENERIC_VIEW = ("View ", "slow")
# a device no module has a profile for: it gets each module's default.lua, as any joystick
GENERIC_DEVICE = "HOTAS Kneeboard generic joystick"


def generic_view_only(commands: set[str]) -> bool:
    return all(c.startswith(GENERIC_VIEW[0]) and c.endswith(GENERIC_VIEW[1]) for c in commands)


def binding_id(b: dict) -> tuple:
    return b["kind"], b["hash"], b["key"], tuple(sorted(b.get("reformers") or []))


def device_specific(device: dict, generic: set[tuple]) -> dict:
    """On a module's default.lua, the device gets what any joystick gets (a panel gets an X axis,
    a stick the Ka-50's Shkval slew): keep only what differs, the diff the module ships for it."""
    if not device.get("base_file", "").replace("\\", "/").endswith("/default.lua"):
        return device
    return device | {"bindings": [b for b in device["bindings"] if binding_id(b) not in generic]}


def bound_inputs(
    result, translate, settings, library, wanted: set[str]
) -> dict[str, dict[str, dict[str, set[str]]]]:
    """template id -> device name -> input -> commands, over every module; only the ``wanted``
    devices (lower case) when given, without what DCS gives any joystick"""
    bound: dict[str, dict[str, dict[str, set[str]]]] = {}
    for profile in result["profiles"].values():
        generic = {
            binding_id(b)
            for d in profile["devices"]
            if d["name"] == GENERIC_DEVICE
            for b in d.get("bindings", [])
        }
        for device in profile["devices"]:
            page = build_page(device_specific(device, generic) if wanted else device, translate)
            if wanted and page.name.lower() not in wanted:
                continue
            chosen = settings.device_templates.get(page.name)
            template = library.get(chosen) if chosen else (None if chosen == "" else library.match(page.name))
            if template is None:
                continue
            inputs = bound.setdefault(template.id, {}).setdefault(page.name, {})
            for key, labels in page.inputs.items():
                for label in labels.values():
                    inputs.setdefault(key, set()).update(label.pressed + label.released)
    return bound


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--install", type=Path, default=None)
    parser.add_argument("--saved-games", type=Path, default=None)
    parser.add_argument(
        "--device",
        action="append",
        default=[],
        help="DCS name of a device (without GUID), checked on the defaults of every installed module",
    )
    args = parser.parse_args()
    install = args.install or detect_dcs_install_dir()
    saved = args.saved_games or detect_saved_games_dir()
    if not install or not saved:
        print("VERDICT: DCS install or Saved Games not found, give --install and --saved-games")
        return 2
    settings = SettingsStore(data_dir() / "settings.json").load()
    library = TemplateLibrary([BUNDLED_DIR], user_dir=data_dir() / "templates")
    translate = command_translator(install, settings.language or detect_language())
    wanted = {name.lower() for name in args.device}
    profiles = list_user_profiles(saved)
    result = load_effective_bindings(
        install,
        saved,
        profiles,
        extra_devices=[*args.device, GENERIC_DEVICE] if wanted else [],
        all_installed=bool(wanted),
    )
    bound = bound_inputs(result, translate, settings, library, wanted)

    problems = 0
    for template_id in sorted(bound):
        template = library.get(template_id)
        boxes = set(template.data["inputs"])
        checked = template.data.get("checked")
        for device, inputs in sorted(bound[template_id].items()):
            missing = {k: c for k, c in inputs.items() if k not in boxes and not generic_view_only(c)}
            status = "OK" if not missing else "À VÉRIFIER"
            note = f" (vérifié : {checked['by']}, {checked['date']})" if checked else ""
            print(
                f"{status:11} {template_id} ← {device}{note}: {len(inputs)} entrées liées, {len(missing)} sans case"
            )
            for key in sorted(missing, key=lambda k: (len(k), k)):
                print(f"    {key:16} {' / '.join(sorted(missing[key]))[:110]}")
            problems += bool(missing)
    seen = {device.lower() for devices in bound.values() for device in devices}
    for name in args.device:
        if name.lower() not in seen:
            print(f"INTROUVABLE {name}: aucun module ne le connaît, ou aucun gabarit ne lui correspond")
            problems += 1
    print(f"VERDICT: {problems} template(s) to check on the device, of {len(bound)} in use")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
