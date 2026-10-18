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

import io
import json
import logging
import re
import shutil
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

_logger = logging.getLogger(__name__)

FORMAT = 1
BUNDLED_DIR = Path(__file__).parent / "library"
IMAGE_TYPES = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


TEMPLATE_FILE = "template.json"
# a shared template file: template.json and its picture, nothing else, of a reasonable size
MAX_IMAGE_BYTES = 20 * 1024 * 1024
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class TemplateError(ValueError):
    pass


def slug(name: str) -> str:
    """Folder id of a template: "Thrustmaster Warthog - Throttle" -> "thrustmaster-warthog-throttle" """
    text = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")[:64].strip("-")
    return text or "template"


@dataclass
class Template:
    id: str
    folder: Path
    data: dict
    user: bool = False  # in the user's folder: can be changed or deleted

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
            "user": self.user,
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
    """Bundled templates, then the user's (``user_dir``), which win on the same id."""

    def __init__(self, folders: list[Path], user_dir: Path | None = None):
        self.folders = [*folders, user_dir] if user_dir else folders
        self.user_dir = user_dir
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
                    found[folder.name] = Template(folder.name, folder, data, user=root == self.user_dir)
            self._templates = found
        return self._templates

    def get(self, template_id: str) -> Template | None:
        return self.templates.get(template_id)

    def match(self, device_name: str) -> Template | None:
        """Template listing this DCS device name (without GUID), ignoring case; the user's first."""
        wanted = device_name.casefold()
        ordered = sorted(self.templates.values(), key=lambda t: not t.user)
        for template in ordered:
            if any(d.casefold() == wanted for d in template.data.get("devices", [])):
                return template
        return None

    # --- the user's templates --------------------------------------------------------------

    def _user_folder(self, template_id: str) -> Path:
        if self.user_dir is None:
            raise TemplateError("no folder for the user's templates")
        if not _ID.match(template_id):
            raise TemplateError(f"identifiant de gabarit invalide : {template_id!r}")
        return self.user_dir / template_id

    def save(self, template_id: str, data: dict, image_name: str, image: bytes) -> Template:
        """Writes a template into the user's folder, replacing one with the same id.

        Written in a new folder first, which takes the place of the old one once valid."""
        folder = self._user_folder(template_id)
        suffix = Path(image_name).suffix.lower()
        if suffix not in IMAGE_TYPES:
            raise TemplateError(f"image : {', '.join(IMAGE_TYPES)} attendu")
        if not image or len(image) > MAX_IMAGE_BYTES:
            raise TemplateError("image vide ou trop grande (20 Mo au plus)")
        data = {k: v for k, v in data.items() if k != "id"} | {
            "format": FORMAT,
            "image": f"background{suffix}",
        }
        staging = folder.with_name(f".{template_id}.{uuid.uuid4().hex}")
        staging.mkdir(parents=True)
        try:
            (staging / data["image"]).write_bytes(image)
            validate(data, staging)
            (staging / TEMPLATE_FILE).write_text(
                json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8"
            )
            if folder.exists():
                old = folder.with_name(f".{template_id}.old.{uuid.uuid4().hex}")
                folder.replace(old)
                staging.replace(folder)
                shutil.rmtree(old, ignore_errors=True)
            else:
                staging.replace(folder)
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        self.reload()
        return self.templates[template_id]

    def delete(self, template_id: str) -> None:
        template = self.get(template_id)
        if template is None or not template.user:
            raise TemplateError("seuls tes propres gabarits peuvent être supprimés")
        shutil.rmtree(template.folder)
        self.reload()

    def export_file(self, template_id: str) -> bytes:
        """The template as one file to share: a zip of template.json and its picture."""
        template = self.get(template_id)
        if template is None:
            raise TemplateError("gabarit introuvable")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(TEMPLATE_FILE, json.dumps(template.data, indent=1, ensure_ascii=False))
            archive.write(template.image_path, template.data["image"])
        return buffer.getvalue()

    def import_file(self, content: bytes) -> Template:
        """A shared template file into the user's folder; its id comes from its name, made unique."""
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                data = json.loads(archive.read(TEMPLATE_FILE).decode("utf-8"))
                image_name = data.get("image") if isinstance(data, dict) else None
                if not isinstance(image_name, str) or Path(image_name).name != image_name:
                    raise TemplateError("fichier de gabarit invalide : pas d'image")
                info = archive.getinfo(image_name)
                if info.file_size > MAX_IMAGE_BYTES:
                    raise TemplateError("image trop grande (20 Mo au plus)")
                image = archive.read(info)
        except (zipfile.BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise TemplateError(f"fichier de gabarit invalide : {error}") from error
        base = slug(str(data.get("name") or "template"))
        template_id, n = base, 2
        while self.get(template_id) is not None:
            template_id, n = f"{base[:60]}-{n}", n + 1
        return self.save(template_id, data, image_name, image)
