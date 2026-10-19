"""Compares the device pages with DCS's own export of the bindings (MAKE HTML in the controls menu).

DCS writes one file per plugged device in ``Saved Games/DCS/InputLayoutsTxt/<profile>/``: one row per
command with its combos, its name and its hash. Two checks per device:

- engine: the (hash, combo) pairs, which do not depend on the game's language;
- page: every (combo, command name) of the export is on the page the app shows, a switch's released
  position (``JOY_BTN17_OFF``) and the modifier layers included; and the page shows nothing else.
  The names are compared as the game shows them, translated into its language.

Usage: uv run python scripts/compare_make_html.py "A-10C II" [more profiles]
         [--install "C:/jeux/DCS World"] [--saved-games "C:/Users/<you>/Saved Games/DCS"] [--language en]
The last line is the verdict.
"""

import argparse
import html
import re
import sys
from pathlib import Path

from hotas_kneeboard.dcs import command_translator, detect_language, detect_saved_games_dir
from hotas_kneeboard.engine import detect_dcs_install_dir, load_effective_bindings
from hotas_kneeboard.pages import RELEASED_SUFFIX, build_page

ROW = re.compile(r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*</tr>", re.S)


def combo_string(key: str, reformers: list[str]) -> str:
    # as Scripts/Input/MakeLayoutText.lua writes it: sorted modifiers, then the key
    return " - ".join([*sorted(reformers), key])


def read_export(path: Path) -> dict[tuple[str, str], str]:
    """(hash, combo) -> command name"""
    pairs = {}
    for combos, name, _category, hash_ in ROW.findall(path.read_text(encoding="utf-8", errors="replace")):
        for combo in filter(None, (c.strip() for c in html.unescape(combos).split(";"))):
            pairs[(html.unescape(hash_).strip(), combo)] = html.unescape(name).strip()
    return pairs


def page_pairs(page) -> set[tuple[str, str]]:
    """(combo, command name) shown on a page"""
    shown = set()
    for key, labels in page.inputs.items():
        for layer, label in labels.items():
            reformers = layer.split(" + ") if layer else []
            for command in label.pressed:
                shown.add((combo_string(key, reformers), command))
            for command in label.released:
                shown.add((combo_string(key + RELEASED_SUFFIX, reformers), command))
    return shown


def compare_profile(result: dict, saved_games: Path, profile: str, translate) -> tuple[int, int]:
    export_dir = saved_games / "InputLayoutsTxt" / profile
    # the GUID changes case between the export and the diff file names (11f0 / 11F0)
    exports = {p.stem.lower(): p for p in export_dir.glob("*.html") if p.stem not in ("Keyboard", "Mouse")}
    if not exports:
        print(f"{profile}: no DCS export in {export_dir} (click MAKE HTML in the game's controls)")
        return 0, 1
    devices = {d["name"].lower(): d for d in result["profiles"][profile]["devices"]}
    same = differences = 0
    for name in sorted(exports):
        theirs = read_export(exports[name])
        device = devices.get(name)
        label = exports[name].stem.split(" {")[0]
        if device is None:
            print(f"ÉCART  {profile} / {label}: no device in Saved Games/DCS/Config/Input")
            differences += len(theirs)
            continue
        ours = {(b["hash"], combo_string(b["key"], b["reformers"])): b["command"] for b in device["bindings"]}
        engine_missing = set(theirs) - set(ours)
        engine_extra = set(ours) - set(theirs)
        expected = {(combo, command) for (_h, combo), command in theirs.items()}
        shown = page_pairs(build_page(device, translate))
        page_missing = expected - shown
        page_extra = shown - expected
        problems = len(engine_missing) + len(engine_extra) + len(page_missing) + len(page_extra)
        same += len(expected & shown)
        differences += problems
        print(
            f"{'OK' if not problems else 'ÉCART':6} {profile} / {label}: {len(expected & shown)} shown as in DCS"
            + (
                f", engine {len(engine_missing)} missing {len(engine_extra)} extra,"
                f" page {len(page_missing)} missing {len(page_extra)} extra"
                if problems
                else ""
            )
        )
        for combo, command in sorted(page_missing):
            print(f"    missing on the page  {combo:30} {command}")
        for combo, command in sorted(page_extra):
            print(f"    extra on the page    {combo:30} {command}")
        for h, combo in sorted(engine_missing | engine_extra, key=lambda p: p[1]):
            print(
                f"    engine differs       {combo:30} {theirs.get((h, combo)) or ours.get((h, combo))} [{h}]"
            )
    return same, differences


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("profiles", nargs="+")
    parser.add_argument("--install", type=Path, default=None)
    parser.add_argument("--saved-games", type=Path, default=None)
    parser.add_argument("--language", default=None, help="the game's language by default (registry)")
    args = parser.parse_args()
    install = args.install or detect_dcs_install_dir()
    saved_games = args.saved_games or detect_saved_games_dir()
    if not install or not saved_games:
        print("VERDICT: DCS install or Saved Games not found, give --install and --saved-games")
        return 2
    result = load_effective_bindings(install, saved_games, args.profiles)
    translate = command_translator(install, args.language or detect_language())
    same = differences = 0
    for profile in args.profiles:
        s, d = compare_profile(result, saved_games, profile, translate)
        same, differences = same + s, differences + d
    if differences:
        print(f"VERDICT: {differences} differences ({same} bindings shown as in DCS)")
        return 1
    print(f"VERDICT: pages identical to DCS's export ({same} bindings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
