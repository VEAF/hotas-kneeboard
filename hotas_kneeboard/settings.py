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
    # modifier layers on the same page as the base layer, or one page per layer
    layer_mode: str = "merge"
    # height of the kneeboard PNG, in pixels; the width follows the page's proportions
    page_height: int = 1024

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        known = {f.name for f in fields(cls)}
        settings = cls(**{k: v for k, v in data.items() if k in known})
        settings.validate()
        return settings

    def validate(self) -> None:  # noqa: C901
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
        if not _is_map(self.exported, lambda v: _is_map(v, lambda b: isinstance(b, bool))):
            raise ValueError("exported : profil -> {périphérique: true/false} attendu")
        if not _is_map(
            self.device_order, lambda v: isinstance(v, list) and all(isinstance(d, str) for d in v)
        ):
            raise ValueError("device_order : profil -> liste de périphériques attendu")
        if not _is_map(self.device_templates, lambda v: isinstance(v, str)):
            raise ValueError("device_templates : périphérique -> gabarit attendu")
        if self.layer_mode not in LAYER_MODES:
            raise ValueError(f"calques : {' ou '.join(LAYER_MODES)} attendu")
        if isinstance(self.page_height, bool) or not isinstance(self.page_height, int | float):
            raise ValueError("hauteur des pages : nombre attendu")
        if not 256 <= int(self.page_height) <= 4096:
            raise ValueError("hauteur des pages : entre 256 et 4096 pixels")
        self.page_height = int(self.page_height)

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
