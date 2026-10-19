"""HTTP server: reads DCS, serves the UI and the templates, writes the kneeboard pages, and changes
DCS's own input files (with a backup first, see dcs_config.py).

Error messages reach the user as they are: they are written in the language of the interface
that asked (``i18n.LanguageMiddleware``)."""

import base64
import binascii
import logging
import threading
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .dcs import command_translator, resolve_dirs
from .dcs_config import (
    BackupNotFoundError,
    BackupStore,
    DcsConfigError,
    absent_devices,
    dcs_log_date,
    dcs_running,
    deleted_modifiers,
    disabled_devices,
    fix_modifiers,
    forget_device,
    modifier_issues,
    remove_bindings,
    restore,
    restore_modifiers,
    seen_devices,
    set_device_disabled,
)
from .engine import EffectiveBindingsError, list_user_profiles, load_effective_bindings
from .generic_buttons import is_generic_base, removable, remove_generic_buttons
from .generic_buttons import plan as generic_buttons_plan
from .hat_views import plan as hat_views_plan
from .hat_views import remove_hat_views
from .i18n import LanguageMiddleware, current_language, t
from .kneeboard import KneeboardError, write_pages
from .pages import build_page, split_device_name
from .programs import read_programs
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


class DeviceDisabled(BaseModel):
    device: str  # full name, with its GUID
    disabled: bool


class DeviceForget(BaseModel):
    device: str  # full name, with its GUID


class HatViewsRemoval(BaseModel):
    devices: list[str]  # full names, with their GUID
    every_device: bool = False
    all_modules: bool = False


class BindingRef(BaseModel):
    """One binding, as the engine names it: the command's hash and the combo"""

    kind: Literal["key", "axis"]
    hash: str
    key: str
    reformers: list[str] = []


class BindingsRemoval(BaseModel):
    profile: str  # the folder in Saved Games/DCS/Config/Input
    device: str  # full name, with its GUID: the diff file's name
    bindings: list[BindingRef]


class GenericButtonsRemoval(BaseModel):
    all_modules: bool = False


class ModifiersRestore(BaseModel):
    profile: str
    backup: str  # backup id


class TemplateImport(BaseModel):
    file: str  # base64 of the shared template file


def _b64(data: str) -> bytes:
    try:
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise HTTPException(422, t("api.bad_base64")) from error


class Bindings:
    """Engine output turned into pages, computed once and on demand: one run reads every module."""

    def __init__(self, lua_interpreter: str | None = None):
        self.lua_interpreter = lua_interpreter
        self._lock = threading.Lock()
        self._cache: dict | None = None
        self._language = ""

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None

    def get(self, dirs: dict, library: TemplateLibrary, refresh: bool = False) -> dict:
        with self._lock:
            # an error is a message, in the language of the request that computed it: computed again
            # for a request in another language (the pages themselves speak DCS's language)
            stale = self._cache is not None and self._cache["error"] and self._language != current_language()
            if self._cache is None or refresh or stale:
                self._cache = self._compute(dirs, library, self.lua_interpreter)
                self._language = current_language()
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
            return {"profiles": [], "error": t("bindings.read_failed", error=error)}
        translate = command_translator(install, dirs["language"])
        try:
            disabled = {name.lower() for name in disabled_devices(install, saved, lua_interpreter)}
        except DcsConfigError as error:
            _logger.warning(f"disabled devices unknown: {error}")
            disabled = set()
        # modifiers DCS drops (device renamed): their layers do not fire in game
        inactive: dict[str, set[str]] = {}
        for issue in modifier_issues(install, saved, lua_interpreter):
            inactive.setdefault(issue["profile"], set()).add(issue["modifier"])
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
                        "dcs_disabled": page.full_name.lower() in disabled,
                        "inactive_modifiers": sorted(
                            {m for layer in page.layers for m in layer.split(" + ")}
                            & inactive.get(name, set())
                        ),
                    }
                )
            profiles.append(
                {
                    "name": name,
                    "display_name": translate(entry["display_name"]) if entry.get("display_name") else None,
                    "unit_type": entry.get("unit_type"),
                    "found": entry["found"],
                    "devices": devices,
                }
            )
        for profile, label in zip(profiles, profile_labels(profiles), strict=True):
            profile["display_name"] = label
        # in the order of the names shown, which the module list and "all the modules" follow
        profiles.sort(key=lambda p: p["display_name"].casefold())
        return {"profiles": profiles, "error": None}


def binding_origin(binding: dict, generic_base: bool) -> str:
    """ "user": the user placed it; "device": the module placed it for this very device (its profile
    for the device, or the diff it ships for it); "generic": the module's profile of any joystick
    (the Gun Trigger on button 1 of a throttle), often a binding to remove"""
    if binding.get("from_diff"):
        return "user"
    if binding.get("from_module_diff") or not generic_base:
        return "device"
    return "generic"


def profile_labels(profiles: list[dict]) -> list[str]:
    """The name each profile shows: DCS's (its folder's name.lua), else its folder's; two profiles
    of the same name (an old folder DCS kept, "Mi-24P Pilot" and "Mi-24P_pilot") say their folder"""
    names = [p.get("display_name") or p["name"] for p in profiles]
    counts = Counter(n.casefold() for n in names)
    return [
        f"{label} ({p['name']})" if counts[label.casefold()] > 1 and label != p["name"] else label
        for label, p in zip(names, profiles, strict=True)
    ]


def create_app(
    store: SettingsStore | None = None,
    library: TemplateLibrary | None = None,
    lua_interpreter: str | None = None,
    backups: BackupStore | None = None,
    is_dcs_running: Callable[[], bool] = dcs_running,
) -> FastAPI:
    """``lua_interpreter``: another Lua 5.1 than the install's ``bin/luae.exe`` (tests);
    ``is_dcs_running``: whether DCS runs, checked before any change to its files."""
    store = store or SettingsStore(data_dir() / "settings.json")
    backups = backups or BackupStore(data_dir() / "backups")
    library = library or TemplateLibrary([BUNDLED_DIR], user_dir=data_dir() / "templates")
    bindings = Bindings(lua_interpreter)
    settings_lock = threading.Lock()
    app = FastAPI(title="HOTAS Kneeboard", version=__version__)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=LOCAL_HOSTS)

    @app.middleware("http")
    async def same_origin_writes(request: Request, call_next):
        refused = JSONResponse({"detail": t("api.other_site")}, status_code=403)
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
            if urlsplit(origin).hostname not in LOCAL_HOSTS:
                return refused
        # a read too runs the engine: a page of another site may send it, without seeing the answer
        if request.url.path.startswith("/api/") and request.headers.get("sec-fetch-site") == "cross-site":
            return refused
        return await call_next(request)

    # added last, so it runs first: every answer, a refusal above included, in the request's language
    app.add_middleware(LanguageMiddleware)

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
        return {
            "version": __version__,
            "dcs": current_dirs(),
            "settings": store.load().as_dict(),
            "settings_file": str(store.path),
        }

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

    @app.get("/api/programs")
    def get_programs(pages: str | None = None) -> dict:
        """Buttons other programs use (SRS, VectorXR, entered by hand); read each time: cheap, and
        the user may change them while the app runs. Their actions in ``pages``, the language of the
        pages they are drawn on; the problems in the request's, shown in the interface."""
        dirs = current_dirs()
        saved = dirs["saved_games_dir"]
        profiles = list_user_profiles(Path(saved)) if saved else []
        return read_programs(store.load().srs_dir, profiles, pages)

    @app.get("/api/templates")
    def list_templates() -> list[dict]:
        bundled = library.bundled_ids()
        return [
            t.summary() | {"replaces_bundled": t.user and t.id in bundled} for t in library.templates.values()
        ]

    @app.get("/api/templates/{template_id}")
    def get_template(template_id: str) -> dict:
        template = library.get(template_id)
        if template is None:
            raise HTTPException(404, t("template.missing"))
        return template.data | {"id": template.id, "user": template.user}

    @app.get("/api/templates/{template_id}/image")
    def get_template_image(template_id: str) -> FileResponse:
        template = library.get(template_id)
        if template is None:
            raise HTTPException(404, t("template.missing"))
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
        # devices given this template by hand go back to the automatic match
        with settings_lock:
            settings = store.load()
            kept = {d: t for d, t in settings.device_templates.items() if t != template_id}
            if kept != settings.device_templates:
                settings.device_templates = kept
                store.save(settings)
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
            raise HTTPException(409, t("dcs.saved_games_missing"))
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
            raise HTTPException(500, t("kneeboard.write_failed", error=error)) from error

    def saved_games_or_409() -> Path:
        saved = current_dirs()["saved_games_dir"]
        if not saved:
            raise HTTPException(409, t("dcs.saved_games_missing"))
        return Path(saved)

    def dcs_state() -> bool | None:
        try:
            return is_dcs_running()
        except DcsConfigError:
            return None

    @app.get("/api/dcs-config/backups")
    def list_backups() -> dict:
        return {
            "folder": str(backups.folder),
            "dcs_running": dcs_state(),
            "backups": [b.as_dict() for b in backups.list()],
        }

    @app.post("/api/dcs-config/backups")
    def create_backup() -> dict:
        try:
            return backups.create(saved_games_or_409() / "Config" / "Input", t("backup.by_hand")).as_dict()
        except DcsConfigError as error:
            raise HTTPException(422, str(error)) from error

    @app.post("/api/dcs-config/backups/{backup_id}/restore")
    def restore_backup(backup_id: str) -> dict:
        try:
            before = restore(saved_games_or_409(), backups, backup_id, is_dcs_running)
        except BackupNotFoundError as error:
            raise HTTPException(404, str(error)) from error
        except DcsConfigError as error:
            raise HTTPException(409, str(error)) from error
        bindings.invalidate()
        return {"restored": backup_id, "backup_before": before.as_dict()}

    def install_and_saved() -> tuple[Path, Path]:
        dirs = current_dirs()
        if dirs["problems"]:
            raise HTTPException(409, " ; ".join(dirs["problems"]))
        return Path(dirs["install_dir"]), Path(dirs["saved_games_dir"])

    @app.get("/api/dcs-config/devices")
    def dcs_devices() -> dict:
        install, saved = install_and_saved()
        try:
            disabled = disabled_devices(install, saved, lua_interpreter)
        except DcsConfigError as error:
            raise HTTPException(422, str(error)) from error
        logged = dcs_log_date(saved)
        return {
            "disabled": disabled,
            "seen": seen_devices(saved),
            "absent": absent_devices(saved, disabled),
            "log_date": logged.isoformat(timespec="seconds") if logged else None,
        }

    @app.post("/api/dcs-config/devices/forget")
    def post_forget_device(body: DeviceForget) -> dict:
        install, saved = install_and_saved()
        try:
            disabled = disabled_devices(install, saved, lua_interpreter)
            backup, profiles = forget_device(saved, backups, body.device, disabled, is_running=is_dcs_running)
        except DcsConfigError as error:
            raise HTTPException(409, str(error)) from error
        bindings.invalidate()
        return {"profiles": profiles, "backup": backup.as_dict()}

    @app.put("/api/dcs-config/devices/disabled")
    def put_device_disabled(body: DeviceDisabled) -> dict:
        install, saved = install_and_saved()
        try:
            backup = set_device_disabled(
                install,
                saved,
                backups,
                body.device,
                body.disabled,
                is_running=is_dcs_running,
                lua_interpreter=lua_interpreter,
            )
        except DcsConfigError as error:
            raise HTTPException(409, str(error)) from error
        bindings.invalidate()
        return {"backup": backup.as_dict()}

    @app.get("/api/dcs-config/hat-views")
    def get_hat_views(all_modules: bool = False) -> dict:
        """Preview: the devices whose hat carries the 8 generic views, and where; nothing written"""
        install, saved = install_and_saved()
        try:
            devices = hat_views_plan(install, saved, all_modules=all_modules, lua_interpreter=lua_interpreter)
        except DcsConfigError as error:
            raise HTTPException(422, str(error)) from error
        return {"all_modules": all_modules, "devices": devices}

    @app.post("/api/dcs-config/hat-views")
    def post_hat_views(body: HatViewsRemoval) -> dict:
        install, saved = install_and_saved()
        try:
            result = remove_hat_views(
                install,
                saved,
                backups,
                body.devices,
                every_device=body.every_device,
                all_modules=body.all_modules,
                is_running=is_dcs_running,
                lua_interpreter=lua_interpreter,
            )
        except DcsConfigError as error:
            raise HTTPException(409, str(error)) from error
        finally:
            # even a write stopped halfway may have changed files
            bindings.invalidate()
        return result

    @app.get("/api/dcs-config/generic-buttons")
    def get_generic_buttons(all_modules: bool = False) -> dict:
        """Preview: the buttons DCS gives the devices marked as having none, and where"""
        install, saved = install_and_saved()
        names = store.load().buttonless_devices
        try:
            devices = generic_buttons_plan(
                install, saved, names, all_modules=all_modules, lua_interpreter=lua_interpreter
            )
        except DcsConfigError as error:
            raise HTTPException(422, str(error)) from error
        translate = command_translator(install, current_dirs()["language"])
        for d in devices:
            for m in d["modules"]:
                for b in m["bindings"]:
                    b["command"] = translate(b["command"])
        return {"all_modules": all_modules, "marked": names, "devices": devices}

    @app.post("/api/dcs-config/generic-buttons")
    def post_generic_buttons(body: GenericButtonsRemoval) -> dict:
        install, saved = install_and_saved()
        try:
            result = remove_generic_buttons(
                install,
                saved,
                backups,
                store.load().buttonless_devices,
                all_modules=body.all_modules,
                is_running=is_dcs_running,
                lua_interpreter=lua_interpreter,
            )
        except DcsConfigError as error:
            raise HTTPException(409, str(error)) from error
        finally:
            # even a write stopped halfway may have changed files
            bindings.invalidate()
        return result

    @app.get("/api/dcs-config/bindings")
    def get_device_bindings(profile: str, device: str) -> dict:
        """Every binding of a device in a module, one row each, for the user to pick what to remove,
        with its origin (see ``binding_origin``)"""
        install, saved = install_and_saved()
        # only a module the user configured: the name goes to the engine
        if profile not in list_user_profiles(saved):
            raise HTTPException(404, t("api.unknown_module", module=repr(profile)))
        try:
            result = load_effective_bindings(install, saved, [profile], lua_interpreter)
        except EffectiveBindingsError as error:
            raise HTTPException(422, t("bindings.read_failed", error=error)) from error
        entry = result["profiles"].get(profile) or {}
        found = next((d for d in entry.get("devices", []) if d["name"].lower() == device.lower()), None)
        if found is None:
            raise HTTPException(404, t("api.device_not_configured", device=device, module=profile))
        translate = command_translator(install, current_dirs()["language"])
        generic_base = is_generic_base(found.get("base_file"))
        return {
            "profile": profile,
            "device": found["name"],
            # a device DCS knows only by its diff (module not installed): nothing to compute from
            "editable": found.get("source") == "effective",
            "bindings": [
                {
                    "kind": b["kind"],
                    "hash": b["hash"],
                    "key": b["key"],
                    "reformers": b.get("reformers") or [],
                    "command": translate(b["command"]),
                    "category": b.get("category"),
                    "origin": binding_origin(b, generic_base),
                    # an engine command whose number is unknown: its removal cannot be written
                    "removable": removable(b),
                }
                for b in found["bindings"]
            ],
        }

    @app.post("/api/dcs-config/bindings/remove")
    def post_remove_bindings(body: BindingsRemoval) -> dict:
        install, saved = install_and_saved()
        if not body.bindings:
            raise HTTPException(422, t("api.no_binding"))
        if body.profile not in list_user_profiles(saved):
            raise HTTPException(404, t("api.unknown_module", module=repr(body.profile)))
        removals = [{"profile": body.profile, "device": body.device, **b.model_dump()} for b in body.bindings]
        count = len(body.bindings)
        try:
            backup, rewrites = remove_bindings(
                install,
                saved,
                backups,
                removals,
                t(
                    "bindings.reason.one" if count == 1 else "bindings.reason.other",
                    n=count,
                    device=body.device,
                    module=body.profile,
                ),
                is_running=is_dcs_running,
                lua_interpreter=lua_interpreter,
            )
        except DcsConfigError as error:
            raise HTTPException(409, str(error)) from error
        finally:
            # even a write stopped halfway may have changed files
            bindings.invalidate()
        removed = sum(r["removed"] or 0 for r in rewrites)
        return {"backup": backup.as_dict(), "removed": removed, "asked": count}

    @app.get("/api/dcs-config/modifiers")
    def get_modifiers() -> dict:
        """Modifiers DCS drops because their device was renamed, and deleted modifiers.lua files a
        backup still holds; nothing written"""
        install, saved = install_and_saved()
        return {
            "issues": modifier_issues(install, saved, lua_interpreter),
            "deleted": deleted_modifiers(saved, backups),
        }

    @app.post("/api/dcs-config/modifiers/fix")
    def post_fix_modifiers() -> dict:
        install, saved = install_and_saved()
        try:
            backup, fixed = fix_modifiers(
                install, saved, backups, is_running=is_dcs_running, lua_interpreter=lua_interpreter
            )
        except DcsConfigError as error:
            raise HTTPException(409, str(error)) from error
        finally:
            bindings.invalidate()
        return {"fixed": fixed, "backup": backup.as_dict()}

    @app.post("/api/dcs-config/modifiers/restore")
    def post_restore_modifiers(body: ModifiersRestore) -> dict:
        install, saved = install_and_saved()
        try:
            backup, fixed = restore_modifiers(
                install,
                saved,
                backups,
                body.profile,
                body.backup,
                is_running=is_dcs_running,
                lua_interpreter=lua_interpreter,
            )
        except BackupNotFoundError as error:
            raise HTTPException(404, str(error)) from error
        except DcsConfigError as error:
            raise HTTPException(409, str(error)) from error
        finally:
            bindings.invalidate()
        return {"fixed": fixed, "backup": backup.as_dict()}

    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app
