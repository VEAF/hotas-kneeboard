"""HTTP server: reads DCS, serves the UI and the templates, writes the kneeboard pages.

Error messages reach the user as they are: they are written in French, like the UI."""

import base64
import binascii
import logging
import threading
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .dcs import command_translator, resolve_dirs
from .engine import EffectiveBindingsError, list_user_profiles, load_effective_bindings
from .kneeboard import KneeboardError, write_pages
from .pages import build_page, split_device_name
from .settings import Settings, SettingsStore, data_dir
from .templates import BUNDLED_DIR, IMAGE_TYPES, TemplateError, TemplateLibrary, slug

_logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent / "web"
# the server listens on 127.0.0.1 only; checking the Host and the Origin also stops a web page from
# reaching it through a domain name pointed at 127.0.0.1 (DNS rebinding)
LOCAL_HOSTS = ["127.0.0.1", "localhost"]


class KneeboardPage(BaseModel):
    title: str
    png: str  # base64


class KneeboardExport(BaseModel):
    unit_type: str
    profile: str
    pages: list[KneeboardPage]


class TemplateSave(BaseModel):
    template: dict
    image_name: str
    image: str  # base64
    # None: a new template, its id made from its name; else the user template to replace
    id: str | None = None


class TemplateImport(BaseModel):
    file: str  # base64 of the shared template file


def _b64(data: str) -> bytes:
    try:
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HTTPException(422, "données illisibles (base64)") from error


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
            return {"profiles": [], "error": f"Lecture des liaisons impossible : {error}"}
        translate = command_translator(install, dirs["language"])
        profiles = []
        for name in names:
            entry = result["profiles"].get(name) or {"found": False, "devices": []}
            devices = []
            for device in entry["devices"]:
                page = build_page(device, translate)
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
    library = library or TemplateLibrary([BUNDLED_DIR], user_dir=data_dir() / "templates")
    bindings = Bindings(lua_interpreter)
    settings_lock = threading.Lock()
    app = FastAPI(title="HOTAS Kneeboard", version=__version__)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=LOCAL_HOSTS)

    @app.middleware("http")
    async def same_origin_writes(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
            if urlsplit(origin).hostname not in LOCAL_HOSTS:
                return JSONResponse({"detail": "requête d'un autre site refusée"}, status_code=403)
        return await call_next(request)

    def current_dirs() -> dict:
        settings = store.load()
        return resolve_dirs(
            settings.dcs_install_dir,
            settings.saved_games_dir,
            own_interpreter=bool(lua_interpreter),
            language_override=settings.language,
        )

    @app.get("/api/state")
    def state() -> dict:
        return {"version": __version__, "dcs": current_dirs(), "settings": store.load().as_dict()}

    @app.put("/api/settings")
    def put_settings(changes: dict) -> dict:
        with settings_lock:  # read, merge, write: two requests must not interleave
            old = store.load()
            try:
                new = Settings.from_dict(old.as_dict() | changes)
            except (TypeError, ValueError) as error:
                raise HTTPException(422, str(error)) from error
            store.save(new)
        read = ("dcs_install_dir", "saved_games_dir", "language")
        if any(getattr(new, field) != getattr(old, field) for field in read):
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
            raise HTTPException(404, "gabarit introuvable")
        return template.data | {"id": template.id}

    @app.get("/api/templates/{template_id}/image")
    def get_template_image(template_id: str) -> FileResponse:
        template = library.get(template_id)
        if template is None:
            raise HTTPException(404, "gabarit introuvable")
        path = template.image_path
        # a user's SVG template opened on its own must not run scripts with access to the API
        return FileResponse(
            path,
            media_type=IMAGE_TYPES[path.suffix.lower()],
            headers={"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"},
        )

    def template_changed() -> None:
        # the automatic matches of the devices may change
        library.reload()
        bindings.invalidate()

    @app.post("/api/templates")
    def save_template(body: TemplateSave) -> dict:
        template_id = body.id
        if template_id is None:
            base, n = slug(str(body.template.get("name") or "")), 1
            template_id = base
            while library.get(template_id) is not None:
                n += 1
                template_id = f"{base[:60]}-{n}"
        try:
            template = library.save(template_id, body.template, body.image_name, _b64(body.image))
        except TemplateError as error:
            raise HTTPException(422, str(error)) from error
        template_changed()
        return template.summary()

    @app.post("/api/templates/import")
    def import_template(body: TemplateImport) -> dict:
        try:
            template = library.import_file(_b64(body.file))
        except TemplateError as error:
            raise HTTPException(422, str(error)) from error
        template_changed()
        return template.summary()

    @app.delete("/api/templates/{template_id}")
    def delete_template(template_id: str) -> dict:
        try:
            library.delete(template_id)
        except TemplateError as error:
            raise HTTPException(422, str(error)) from error
        template_changed()
        return {"deleted": template_id}

    @app.get("/api/templates/{template_id}/file")
    def export_template(template_id: str) -> Response:
        try:
            content = library.export_file(template_id)
        except TemplateError as error:
            raise HTTPException(404, str(error)) from error
        return Response(
            content,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{template_id}.hotas-template.zip"'},
        )

    @app.post("/api/kneeboard")
    def export_kneeboard(export: KneeboardExport) -> dict:
        dirs = current_dirs()
        if not dirs["saved_games_dir"]:
            raise HTTPException(409, "Dossier Saved Games de DCS introuvable : indique-le dans les réglages")
        try:
            return write_pages(
                Path(dirs["saved_games_dir"]),
                export.unit_type,
                export.profile,
                [p.model_dump() for p in export.pages],
            )
        except KneeboardError as error:
            raise HTTPException(422, str(error)) from error
        except OSError as error:
            raise HTTPException(500, f"Pages impossibles à écrire : {error}") from error

    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
