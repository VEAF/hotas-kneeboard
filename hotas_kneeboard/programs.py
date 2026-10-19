"""Buttons other programs use on the same devices: SRS, VectorXR, and any program entered by hand.

Every source gives the same thing, a ``ProgramBinding``: program, device (by its instance GUID, the
same as DCS's), input in DCS's names (``JOY_BTN24``, ``JOY_BTN_POV1_U``) and action. The pages draw
them next to the DCS commands, each program in its colour.

The app only reads these programs' settings, it never writes them.
"""

import configparser
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_logger = logging.getLogger(__name__)

SRS = "SRS"
VECTORXR = "VectorXR"
# profiles SRS keeps next to the per-aircraft ones: not an aircraft's
SRS_NOT_PROFILES = {"global"}
SRS_DEFAULT_PROFILE = "default"
SRS_DEFAULT_DIR = Path("C:/Program Files/DCS-SimpleRadio-Standalone")
SRS_SETTINGS_SECTION = "Client Settings"
# DirectInput's system keyboard: SRS binds keys with it, which are not on any device page
KEYBOARD_GUID = "6f1d2b61-d5a0-11cf-bfc7-444553540000"
# SRS counts buttons from 0, DCS from 1. Measured on the reference PC: in the F-16C_50 the comm
# switch of the Orion F15EX throttle is DCS's "Transmit Switch - UHF / VHF" on JOY_BTN24 / 22, and
# SRS's radio 1 (UHF) / radio 2 (VHF) on its buttons 23 / 21.
SRS_BUTTON_OFFSET = 1
# SRS stores a hat as button 128 + hat index, its value the direction in hundredths of a degree.
# Not seen on the reference PC: to check on the first SRS profile that binds a hat.
SRS_HAT_BASE = 128
# VectorXR reads the devices through Windows Raw Input, whose HID button numbers start at 1 like
# DCS's JOY_BTN. To confirm with a real press: see the lot FEAT-OTHER-APPS-BINDINGS (#24).
VECTORXR_BUTTON_OFFSET = 0

HAT_DIRECTIONS = {
    0: "U",
    4500: "UR",
    9000: "R",
    13500: "DR",
    18000: "D",
    22500: "DL",
    27000: "L",
    31500: "UL",
}

SRS_ACTIONS = {
    "Ptt": "PTT radio",
    "Intercom": "Interphone",
    "IntercomPTT": "PTT interphone",
    "NextRadio": "Radio suivante",
    "PreviousRadio": "Radio précédente",
    "OverlayToggle": "Overlay radio",
    "AwacsOverlayToggle": "Overlay AWACS",
    "RadioChannelUp": "Canal +",
    "RadioChannelDown": "Canal −",
    "RadioVolumeUp": "Volume +",
    "RadioVolumeDown": "Volume −",
    "ToggleGuard": "Garde",
    "ToggleEncryption": "Chiffrement",
    "EncryptionKeyIncrease": "Clé de chiffrement +",
    "EncryptionKeyDecrease": "Clé de chiffrement −",
    "TransponderIDENT": "IDENT transpondeur",
    "ReadoutToggle": "Lecture des fréquences",
}
_SWITCH = re.compile(r"^Switch(\d+)$")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_VECTORXR_BUTTON = re.compile(r"^button-(\d+)$")


@dataclass(frozen=True)
class ProgramBinding:
    program: str
    device_guid: str  # see normalize_guid
    input: str  # DCS's name of the input
    action: str

    def as_dict(self) -> dict:
        return asdict(self)


def normalize_guid(guid: str) -> str:
    """``"{D281FB60-B9AD-…}"`` and ``"d281fb60-b9ad-…"`` are the same device"""
    return guid.strip().strip("{}").lower()


def _button(number: int) -> str:
    return f"JOY_BTN{number}"


# --- SRS ---------------------------------------------------------------------------------------


def srs_action(section: str) -> str:
    if section.startswith("Modifier") and section != "Modifier":
        return f"{srs_action(section.removeprefix('Modifier'))} (modificateur)"
    if match := _SWITCH.match(section):
        return f"Radio {match[1]}"
    return SRS_ACTIONS.get(section) or _CAMEL.sub(" ", section)


def srs_input(button: int, value: int) -> str | None:
    if button >= SRS_HAT_BASE:
        direction = HAT_DIRECTIONS.get(value)
        return f"JOY_BTN_POV{button - SRS_HAT_BASE + 1}_{direction}" if direction else None
    # a button is bound with value 1; anything else is not a button press DCS would show
    return _button(button + SRS_BUTTON_OFFSET) if value == 1 else None


def read_srs_profile(path: Path) -> list[ProgramBinding]:
    """Bindings of one SRS profile (``<profile>.cfg``): an INI section per action"""
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str  # keep the keys' case
    parser.read_string(path.read_text(encoding="utf-8-sig", errors="replace"))
    found = []
    for section in parser.sections():
        if section == SRS_SETTINGS_SECTION:
            continue
        values = parser[section]
        try:
            button, value = int(values["button"]), int(values.get("value", "1"))
        except (KeyError, ValueError):
            continue
        guid = normalize_guid(values.get("guid", ""))
        if guid == KEYBOARD_GUID:
            continue
        key = srs_input(button, value)
        if not guid or key is None:
            _logger.info(f"SRS {path.stem}: {section} skipped (button {button}, value {value})")
            continue
        found.append(ProgramBinding(SRS, guid, key, srs_action(section)))
    return found


def srs_registry_dir() -> Path | None:
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\DCS-SR-Standalone") as key:
            return Path(winreg.QueryValueEx(key, "SRPathStandalone")[0])
    except OSError:
        return None


def srs_profiles_dir(srs_dir: Path) -> Path | None:
    """Where the profiles are: ``Client/`` since SRS 2, the install folder before"""
    for folder in (srs_dir / "Client", srs_dir):
        if folder.is_dir() and any(folder.glob("*.cfg")):
            return folder
    return None


def srs_profile_names(folder: Path) -> list[str]:
    names = [p.stem for p in folder.glob("*.cfg") if p.stem.lower() not in SRS_NOT_PROFILES]
    return sorted(names, key=str.lower)


def _plain(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_srs_profile(dcs_profile: str, srs_names: list[str]) -> str | None:
    """SRS profile of a DCS module, by name: "F-16" for "F-16C_50", "A-10C" for "A-10C II".
    The longest name that starts the other wins; else SRS's default profile."""
    wanted = _plain(dcs_profile)
    candidates = [
        name
        for name in srs_names
        if name.lower() != SRS_DEFAULT_PROFILE
        and _plain(name)
        and (wanted.startswith(_plain(name)) or _plain(name).startswith(wanted))
    ]
    if candidates:
        return max(candidates, key=lambda name: len(_plain(name)))
    return next((name for name in srs_names if name.lower() == SRS_DEFAULT_PROFILE), None)


# --- VectorXR ----------------------------------------------------------------------------------


def vectorxr_settings_file() -> Path | None:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "VectorXR" / "config" / "settings.json" if local else None


def _vectorxr_action(path: list, data: dict) -> str:
    """Readable name of a binding from where it sits in VectorXR's settings"""
    keys = [p for p in path if isinstance(p, str)]
    if keys[:3] == ["core", "osd", "toggleBindings"]:
        return "Overlay : afficher / masquer"
    if keys[:2] == ["core", "osd"]:
        return "Overlay : " + _CAMEL.sub(" ", keys[2]).lower().removesuffix(" binding")
    module = keys[1] if len(keys) > 1 and keys[0] == "modules" else keys[0]
    label = {"pivotxr": "PivotXR", "depthxr": "DepthXR", "quadviews": "Quad views"}.get(module, module)
    if "quickViews" in keys:
        index = path[path.index("quickViews") + 1]
        view = _get(data, path[: path.index("quickViews") + 2]) or {}
        return f"{label} : vue {view.get('name') or index + 1}"
    last = keys[-1] if keys[-1] not in ("binding",) else keys[-2]
    words = {
        "activationBindings": "activer",
        "setOriginBindings": "recentrer",
        "toggleEnabled": "activer / désactiver",
        "toggleAnchor": "ancrage",
    }
    return f"{label} : {words.get(last, _CAMEL.sub(' ', last).lower())}"


def _get(data, path: list):
    for step in path:
        data = data[step]
    return data


def read_vectorxr(path: Path) -> list[ProgramBinding]:
    """Device bindings anywhere in VectorXR's settings. Only what is in use in DCS counts: a
    module or a profile switched off, a profile of another program, are left out."""
    data = json.loads(path.read_text(encoding="utf-8"))
    dcs_apps = {
        a.get("id")
        for a in data.get("applications", [])
        if str(a.get("match", {}).get("exe", "")).lower() == "dcs.exe"
    }
    found: list[ProgramBinding] = []

    def walk(node, where: list) -> None:
        if isinstance(node, dict):
            if node.get("enabled") is False:
                return
            # a profile of another program: its bindings are not used in DCS
            apps = node.get("applicationIds")
            if isinstance(apps, list) and apps and not dcs_apps.intersection(apps):
                return
            if node.get("type") == "device" and "inputPath" in node:
                match = _VECTORXR_BUTTON.match(str(node["inputPath"]))
                if match and node.get("deviceGuid"):
                    found.append(
                        ProgramBinding(
                            VECTORXR,
                            normalize_guid(node["deviceGuid"]),
                            _button(int(match[1]) + VECTORXR_BUTTON_OFFSET),
                            _vectorxr_action(where, data),
                        )
                    )
                else:
                    _logger.info(f"VectorXR: {node.get('inputPath')} at {where} not shown")
                return
            for key, value in node.items():
                walk(value, [*where, key])
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, [*where, index])

    walk(data, [])
    return found


# --- everything --------------------------------------------------------------------------------


def read_programs(srs_dir_setting: str | None, dcs_profiles: list[str]) -> dict:
    """What the programs read directly give the pages: VectorXR's bindings, which hold in every
    module, each SRS profile's bindings, and the SRS profile matched by name to each DCS module.
    The user's choices (another SRS profile, entries by hand, colours) are applied by the UI."""
    problems: list[str] = []

    vectorxr = vectorxr_settings_file()
    vectorxr_bindings: list[dict] = []
    if vectorxr and vectorxr.is_file():
        try:
            vectorxr_bindings = [b.as_dict() for b in read_vectorxr(vectorxr)]
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            problems.append(f"Réglages VectorXR illisibles : {error}")
    else:
        vectorxr = None

    srs_dir = Path(srs_dir_setting) if srs_dir_setting else (srs_registry_dir() or SRS_DEFAULT_DIR)
    folder = srs_profiles_dir(srs_dir)
    srs_names = srs_profile_names(folder) if folder else []
    if srs_dir_setting and not folder:
        problems.append(f"Pas de profil SRS (fichier .cfg) dans {srs_dir}")
    srs_bindings: dict[str, list[dict]] = {}
    for name in srs_names:
        try:
            srs_bindings[name] = [b.as_dict() for b in read_srs_profile(folder / f"{name}.cfg")]
        except (OSError, configparser.Error) as error:
            problems.append(f"Profil SRS {name} illisible : {error}")

    return {
        "srs": {
            "folder": str(folder) if folder else None,
            "profiles": srs_names,
            "matched": {p: match_srs_profile(p, srs_names) for p in dcs_profiles},
            "bindings": srs_bindings,
        },
        "vectorxr": {"file": str(vectorxr) if vectorxr else None, "bindings": vectorxr_bindings},
        "problems": problems,
    }
