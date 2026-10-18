"""User settings and where the app keeps its files: ``%APPDATA%/HOTAS Kneeboard/``."""

import json
import logging
import os
import sys
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

    def validate(self) -> None:
        if self.layer_mode not in LAYER_MODES:
            raise ValueError(f"layer_mode must be one of {LAYER_MODES}")
        if not 256 <= int(self.page_height) <= 4096:
            raise ValueError("page_height must be between 256 and 4096")
        self.page_height = int(self.page_height)

    def as_dict(self) -> dict:
        return asdict(self)


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
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(settings.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)
