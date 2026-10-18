"""Device templates: a folder holding ``template.json`` and the picture of the device.

``template.json`` (format 1)::

    {
      "format": 1,
      "name": "Thrustmaster Warthog - Throttle",
      "devices": ["Throttle - HOTAS Warthog"],     # DCS device names, without GUID
      "image": "background.svg",                    # the device, without any label
      "size": [827, 1168],                          # the picture's coordinate system
      "inputs": {                                   # DCS input names
        "JOY_BTN16": {"box": [330, 28, 90, 30]},    # label box: x, y, width, height
        "JOY_BTN1": {"box": [205, 666, 180, 30], "anchor": [545, 706]},  # + leader line
        "JOY_BTN5": {"box": [10, 10, 80, 20], "more_boxes": [[400, 10, 80, 20]]}  # drawn twice
      },
      "credits": {"author": "…", "source": "…", "license": "GPL-2.0"}
    }

The library ships with the app (``hotas_kneeboard/library``); templates in the user's data
folder (``templates/``) come on top and win over a bundled one with the same folder name.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

_logger = logging.getLogger(__name__)

FORMAT = 1
BUNDLED_DIR = Path(__file__).parent / "library"
IMAGE_TYPES = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


class TemplateError(ValueError):
    pass


@dataclass
class Template:
    id: str
    folder: Path
    data: dict

    @property
    def image_path(self) -> Path:
        return self.folder / self.data["image"]

    def summary(self) -> dict:
        return {
            "id": self.id,
            "name": self.data["name"],
            "devices": self.data.get("devices", []),
            "size": self.data["size"],
            "credits": self.data.get("credits", {}),
        }


def _is_numbers(value, count: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == count
        and all(isinstance(v, int | float) and not isinstance(v, bool) for v in value)
    )


def validate(data: dict, folder: Path) -> None:
    if data.get("format") != FORMAT:
        raise TemplateError(f"format must be {FORMAT}")
    if not isinstance(data.get("name"), str):
        raise TemplateError("no name")
    devices = data.get("devices", [])
    if not (isinstance(devices, list) and all(isinstance(d, str) for d in devices)):
        raise TemplateError("devices must be a list of names")
    image = data.get("image")
    if not isinstance(image, str) or Path(image).name != image:
        raise TemplateError("image must be a file name in the template's folder")
    if Path(image).suffix.lower() not in IMAGE_TYPES:
        raise TemplateError(f"image must be one of {', '.join(IMAGE_TYPES)}")
    if not (folder / image).is_file():
        raise TemplateError(f"image {image} not found")
    if not _is_numbers(data.get("size"), 2):
        raise TemplateError("size must be [width, height]")
    _validate_inputs(data.get("inputs"))


def _validate_inputs(inputs) -> None:
    if not isinstance(inputs, dict):
        raise TemplateError("inputs must be an object")
    for key, entry in inputs.items():
        if not (isinstance(entry, dict) and _is_numbers(entry.get("box"), 4)):
            raise TemplateError(f"{key}: box must be [x, y, width, height]")
        if entry.get("anchor") is not None and not _is_numbers(entry["anchor"], 2):
            raise TemplateError(f"{key}: anchor must be [x, y]")
        more = entry.get("more_boxes", [])
        if not (isinstance(more, list) and all(_is_numbers(b, 4) for b in more)):
            raise TemplateError(f"{key}: more_boxes must be a list of [x, y, width, height]")


class TemplateLibrary:
    def __init__(self, folders: list[Path]):
        self.folders = folders
        self._templates: dict[str, Template] | None = None

    def reload(self) -> None:
        self._templates = None

    @property
    def templates(self) -> dict[str, Template]:
        if self._templates is None:
            found: dict[str, Template] = {}
            for root in self.folders:
                if not root.is_dir():
                    continue
                for folder in sorted(p for p in root.iterdir() if p.is_dir()):
                    try:
                        data = json.loads((folder / "template.json").read_text(encoding="utf-8"))
                        validate(data, folder)
                    except FileNotFoundError:
                        continue
                    except (OSError, ValueError) as error:
                        _logger.warning(f"template {folder} ignored: {error}")
                        continue
                    found[folder.name] = Template(folder.name, folder, data)
            self._templates = found
        return self._templates

    def get(self, template_id: str) -> Template | None:
        return self.templates.get(template_id)

    def match(self, device_name: str) -> Template | None:
        """Template listing this DCS device name (without GUID), ignoring case."""
        wanted = device_name.casefold()
        for template in self.templates.values():
            if any(d.casefold() == wanted for d in template.data.get("devices", [])):
                return template
        return None
