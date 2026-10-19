"""User settings and where the app keeps its files: ``%APPDATA%/HOTAS Kneeboard/``."""

import json
import logging
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

_logger = logging.getLogger(__name__)

APP_NAME = "HOTAS Kneeboard"
LAYER_MODES = ("merge", "split")
COLOR = re.compile(r"#[0-9a-fA-F]{6}")
INPUT = re.compile(r"JOY_[A-Z0-9_]+")
# device_name: shown in the list of entries when the device is not plugged
PROGRAM_BINDING_KEYS = {"program", "device_guid", "device_name", "input", "action"}


def data_dir() -> Path:
    if override := os.environ.get("HOTAS_KNEEBOARD_DATA"):
        return Path(override)
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / APP_NAME
    return Path.home() / ".config" / APP_NAME


@dataclass
class Settings:
    # None: detected (registry for the install, the Saved Games known folder for the other)
    dcs_install_dir: str | None = None
    saved_games_dir: str | None = None
    # language of the command names (DCS's l10n folder: "en", "fr"…); None: the game's own
    language: str | None = None
    # profile -> device full name (with GUID: two devices may share a name) -> page exported or
    # not; a device not listed is exported
    exported: dict[str, dict[str, bool]] = field(default_factory=dict)
    # profile -> device full names, in kneeboard page order; devices not listed come after
    device_order: dict[str, list[str]] = field(default_factory=dict)
    # device name -> template id, chosen by the user over the automatic match ("" = no template)
    device_templates: dict[str, str] = field(default_factory=dict)
    # device names (without GUID) hidden in every module: not listed, not exported (a vJoy, a
    # device unplugged for good)
    hidden_devices: list[str] = field(default_factory=list)
    # device names (without GUID) with no button nor hat, axes only (pedals): the buttons DCS gives
    # them from the profile of any joystick are offered for removal (generic_buttons.py)
    buttonless_devices: list[str] = field(default_factory=list)
    # modifier layers on the same page as the base layer, or one page per layer
    layer_mode: str = "merge"
    # height of the kneeboard PNG, in pixels; the width follows the page's proportions
    page_height: int = 1024
    # drawings whose template has a cut line (split_at) become several pages (kneeboard, PDF)
    split_wide: bool = True
    # other programs' buttons (programs.py): SRS install folder (None: registry, then Program
    # Files), DCS profile -> SRS profile chosen by the user ("" = none), entries made by hand,
    # programs not shown, colour of each program
    srs_dir: str | None = None
    srs_profiles: dict[str, str] = field(default_factory=dict)
    program_bindings: list[dict] = field(default_factory=list)
    hidden_programs: list[str] = field(default_factory=list)
    program_colors: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        known = {f.name for f in fields(cls)}
        settings = cls(**{k: v for k, v in data.items() if k in known})
        settings.validate()
        return settings

    def validate(self) -> None:
        self._validate_reading()
        self._validate_choices()
        if self.layer_mode not in LAYER_MODES:
            raise ValueError(f"calques : {' ou '.join(LAYER_MODES)} attendu")
        if not isinstance(self.split_wide, bool):
            raise ValueError("split_wide : true ou false attendu")
        if isinstance(self.page_height, bool) or not isinstance(self.page_height, int | float):
            raise ValueError("hauteur des pages : nombre attendu")
        if not 256 <= int(self.page_height) <= 4096:
            raise ValueError("hauteur des pages : entre 256 et 4096 pixels")
        self.page_height = int(self.page_height)

    def _validate_reading(self) -> None:
        """What changes what is read from DCS: folders and language"""
        for name in ("dcs_install_dir", "saved_games_dir", "language"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{name} : texte attendu")
        for name in ("dcs_install_dir", "saved_games_dir"):
            value = getattr(self, name)
            # a network path would make the app run a program from another machine
            if value and (value.startswith(("\\\\", "//")) or "://" in value):
                raise ValueError(f"{name} : un dossier de ce PC est attendu, pas un chemin réseau")
        if self.language is not None and not re.fullmatch(r"[a-z]{2}", self.language):
            raise ValueError("langue : un dossier l10n de DCS est attendu, par exemple en")

    def _validate_choices(self) -> None:
        """The user's choices per module and per device"""
        if not _is_map(self.exported, lambda v: _is_map(v, lambda b: isinstance(b, bool))):
            raise ValueError("exported : profil -> {périphérique: true/false} attendu")
        if not _is_map(
            self.device_order, lambda v: isinstance(v, list) and all(isinstance(d, str) for d in v)
        ):
            raise ValueError("device_order : profil -> liste de périphériques attendu")
        if not _is_map(self.device_templates, lambda v: isinstance(v, str)):
            raise ValueError("device_templates : périphérique -> gabarit attendu")
        if not (
            isinstance(self.hidden_devices, list) and all(isinstance(d, str) for d in self.hidden_devices)
        ):
            raise ValueError("hidden_devices : liste de noms de périphériques attendue")
        if not (
            isinstance(self.buttonless_devices, list)
            and all(isinstance(d, str) for d in self.buttonless_devices)
        ):
            raise ValueError("buttonless_devices : liste de noms de périphériques attendue")
        self._validate_programs()

    def _validate_programs(self) -> None:
        """Other programs' buttons"""
        if self.srs_dir is not None and not isinstance(self.srs_dir, str):
            raise ValueError("srs_dir : texte attendu")
        if self.srs_dir and (self.srs_dir.startswith(("\\\\", "//")) or "://" in self.srs_dir):
            raise ValueError("srs_dir : un dossier de ce PC est attendu, pas un chemin réseau")
        if not _is_map(self.srs_profiles, lambda v: isinstance(v, str)):
            raise ValueError("srs_profiles : module -> profil SRS attendu")
        if not (
            isinstance(self.hidden_programs, list) and all(isinstance(p, str) for p in self.hidden_programs)
        ):
            raise ValueError("hidden_programs : liste de logiciels attendue")
        if not _is_map(self.program_colors, lambda v: isinstance(v, str) and bool(COLOR.fullmatch(v))):
            raise ValueError("program_colors : logiciel -> couleur #rrggbb attendu")
        if not isinstance(self.program_bindings, list):
            raise ValueError("program_bindings : liste attendue")
        for entry in self.program_bindings:
            if not (
                isinstance(entry, dict)
                and set(entry) == PROGRAM_BINDING_KEYS
                and all(isinstance(v, str) for v in entry.values())
                and entry["program"].strip()
                and entry["action"].strip()
                and INPUT.fullmatch(entry["input"])
            ):
                raise ValueError("program_bindings : logiciel, périphérique, entrée JOY_… et action attendus")

    def as_dict(self) -> dict:
        return asdict(self)


def _is_map(value, valid_value) -> bool:
    return isinstance(value, dict) and all(isinstance(k, str) and valid_value(v) for k, v in value.items())


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> Settings:
        try:
            return Settings.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return Settings()
        except (OSError, ValueError, TypeError) as error:
            # an unreadable file must not lock the user out: start over, keep the file aside
            _logger.warning(f"settings unreadable ({error}), using defaults")
            try:
                self.path.replace(self.path.with_suffix(".broken.json"))
            except OSError:
                pass
            return Settings()

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f"{self.path.stem}.{uuid.uuid4().hex}.tmp")
        tmp.write_text(json.dumps(settings.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)
