"""HTTP server: reads DCS, serves the UI and the templates, writes the kneeboard pages."""

import logging
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .dcs import resolve_dirs
from .engine import EffectiveBindingsError, list_user_profiles, load_effective_bindings
from .kneeboard import KneeboardError, write_pages
from .pages import build_page, split_device_name
from .settings import Settings, SettingsStore, data_dir
from .templates import BUNDLED_DIR, IMAGE_TYPES, TemplateLibrary

_logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent / "web"


class KneeboardPage(BaseModel):
    title: str
    png: str  # base64


class KneeboardExport(BaseModel):
    unit_type: str
    pages: list[KneeboardPage]


class Bindings:
    """Engine output turned into pages, computed once and on demand: one run reads every module."""

    def __init__(self, lua_interpreter: str | None = None):
        self.lua_interpreter = lua_interpreter
        self._lock = threading.Lock()
        self._cache: dict | None = None

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None

    def get(self, dirs: dict, library: TemplateLibrary, refresh: bool = False) -> dict:
        with self._lock:
            if self._cache is None or refresh:
                self._cache = self._compute(dirs, library, self.lua_interpreter)
            return self._cache

    @staticmethod
    def _compute(dirs: dict, library: TemplateLibrary, lua_interpreter: str | None) -> dict:
        if dirs["problems"]:
            return {"profiles": [], "error": " ; ".join(dirs["problems"])}
        install, saved = Path(dirs["install_dir"]), Path(dirs["saved_games_dir"])
        names = list_user_profiles(saved)
        if not names:
            return {"profiles": [], "error": None}
        try:
            result = load_effective_bindings(install, saved, names, lua_interpreter)
        except EffectiveBindingsError as error:
            _logger.error(f"engine failed: {error}")
            return {"profiles": [], "error": str(error)}
        profiles = []
        for name in names:
            entry = result["profiles"].get(name) or {"found": False, "devices": []}
            devices = []
            for device in entry["devices"]:
                page = build_page(device)
                template = library.match(page.name)
                devices.append(
                    page.as_dict()
                    | {
                        "guid": split_device_name(page.full_name)[1],
                        "auto_template_id": template.id if template else None,
                    }
                )
            profiles.append(
                {
                    "name": name,
                    "unit_type": entry.get("unit_type"),
                    "found": entry["found"],
                    "devices": devices,
                }
            )
        return {"profiles": profiles, "error": None}


def create_app(
    store: SettingsStore | None = None,
    library: TemplateLibrary | None = None,
    lua_interpreter: str | None = None,
) -> FastAPI:
    """``lua_interpreter``: another Lua 5.1 than the install's ``bin/luae.exe`` (tests)."""
    store = store or SettingsStore(data_dir() / "settings.json")
    library = library or TemplateLibrary([BUNDLED_DIR, data_dir() / "templates"])
    bindings = Bindings(lua_interpreter)
    app = FastAPI(title="HOTAS Kneeboard", version=__version__)

    def current_dirs() -> dict:
        settings = store.load()
        return resolve_dirs(
            settings.dcs_install_dir, settings.saved_games_dir, own_interpreter=bool(lua_interpreter)
        )

    @app.get("/api/state")
    def state() -> dict:
        return {"version": __version__, "dcs": current_dirs(), "settings": store.load().as_dict()}

    @app.put("/api/settings")
    def put_settings(changes: dict) -> dict:
        old = store.load()
        try:
            new = Settings.from_dict(old.as_dict() | changes)
        except (TypeError, ValueError) as error:
            raise HTTPException(422, str(error)) from error
        store.save(new)
        if (new.dcs_install_dir, new.saved_games_dir) != (old.dcs_install_dir, old.saved_games_dir):
            bindings.invalidate()
        return {"dcs": current_dirs(), "settings": new.as_dict()}

    @app.get("/api/bindings")
    def get_bindings(refresh: bool = False) -> dict:
        if refresh:
            library.reload()
        return bindings.get(current_dirs(), library, refresh)

    @app.get("/api/templates")
    def list_templates() -> list[dict]:
        return [t.summary() for t in library.templates.values()]

    @app.get("/api/templates/{template_id}")
    def get_template(template_id: str) -> dict:
        template = library.get(template_id)
        if template is None:
            raise HTTPException(404, "no such template")
        return template.data | {"id": template.id}

    @app.get("/api/templates/{template_id}/image")
    def get_template_image(template_id: str) -> FileResponse:
        template = library.get(template_id)
        if template is None:
            raise HTTPException(404, "no such template")
        path = template.image_path
        return FileResponse(path, media_type=IMAGE_TYPES[path.suffix.lower()])

    @app.post("/api/kneeboard")
    def export_kneeboard(export: KneeboardExport) -> dict:
        dirs = current_dirs()
        if not dirs["saved_games_dir"]:
            raise HTTPException(409, "Saved Games/DCS not found")
        try:
            return write_pages(
                Path(dirs["saved_games_dir"]),
                export.unit_type,
                [p.model_dump() for p in export.pages],
            )
        except KneeboardError as error:
            raise HTTPException(422, str(error)) from error
        except OSError as error:
            raise HTTPException(500, f"cannot write the pages: {error}") from error

    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
