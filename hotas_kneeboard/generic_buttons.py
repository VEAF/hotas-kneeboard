"""Removing, in bulk, the buttons DCS gives a device that has none.

A module with no profile for a device gives it its profile of any joystick (``default.lua``): pedals
get a weapon release on button 2, a nosewheel steering on button 4… which nothing can press. The
user says which devices have no button nor hat (``Settings.buttonless_devices``, names without
GUID); their key bindings (buttons and hats) that come from that profile go, in every module in
scope. The user's own bindings, the ones the module plans for this very device, and the axes stay.
The scope is the modules where the device has a diff, or with ``all_modules`` every installed
one (a diff is then created); the single backup and the reading again are those of the hat views
(hat_views.py).
Error messages reach the user as they are: they are in French."""

from collections.abc import Callable
from pathlib import Path

from .dcs_config import (
    BackupStore,
    DcsConfigError,
    dcs_running,
    disabled_devices,
    input_dir_of,
    remove_bindings,
)
from .engine import PATH_TOO_LONG, EffectiveBindingsError, load_effective_bindings
from .hat_views import _configured_profiles, _plugged_devices
from .i18n import t
from .pages import split_device_name


def is_generic_base(base_file: str | None) -> bool:
    """A device DCS gives the profile of any joystick: the module has no profile for it"""
    return bool(base_file) and base_file.replace("\\", "/").lower().endswith("/default.lua")


def is_generic_button(binding: dict, generic_base: bool) -> bool:
    """A button or hat binding from the profile of any joystick: not the user's, not one the module
    ships for this device"""
    return (
        generic_base
        and binding["kind"] == "key"
        and not binding.get("from_diff")
        and not binding.get("from_module_diff")
    )


# a hash naming an engine command (iCommand…) whose number no diff taught the engine: a removal
# cannot be written as DCS would (effective_bindings.lua refuses it)
UNKNOWN_COMMAND = "@"


def removable(binding: dict) -> bool:
    return UNKNOWN_COMMAND not in binding["hash"]


def plan(
    install_dir: Path,
    saved_games_dir: Path,
    devices: list[str],
    *,
    all_modules: bool = False,
    lua_interpreter=None,
) -> list[dict]:
    """The generic buttons of ``devices`` (names without GUID) in the profiles in scope:
    ``[{"device": full name, "name", "modules": [{"profile", "unit_type", "file": the diff file's
    device name, "bindings": [{"hash", "key", "reformers", "command"}], "unknown": [{"key", "command"}]
    the generic ones whose engine command has no known number (not removable), "new_file",
    "error"}]}]``; a device without any is left out."""
    wanted = {d.lower() for d in devices}
    if not wanted:
        return []
    disabled = disabled_devices(install_dir, saved_games_dir, lua_interpreter)
    extra = [
        d for d in _plugged_devices(saved_games_dir, disabled) if split_device_name(d)[0].lower() in wanted
    ]
    try:
        result = load_effective_bindings(
            install_dir,
            saved_games_dir,
            _configured_profiles(saved_games_dir),
            lua_interpreter,
            extra_devices=extra,
            all_installed=all_modules,
        )
    except EffectiveBindingsError as error:
        raise DcsConfigError(t("bindings.read_failed", error=error)) from error
    spelling = {name.lower(): name for name in extra}
    found: dict[str, dict] = {}
    for profile, entry in sorted(result["profiles"].items()):
        if not entry.get("found"):
            continue
        for d in entry["devices"]:
            name = split_device_name(d["name"])[0]
            if d.get("source") != "effective" or name.lower() not in wanted:
                continue
            # by default only the modules where the user configured the device (it has a diff
            # there); every installed module, a new diff where needed, with all_modules
            if d.get("extra") and not all_modules:
                continue
            generic = is_generic_base(d.get("base_file"))
            generics = [
                {
                    "hash": b["hash"],
                    "key": b["key"],
                    "reformers": b.get("reformers") or [],
                    "command": b["command"],
                }
                for b in d["bindings"]
                if is_generic_button(b, generic)
            ]
            if not generics:
                continue
            bindings = [b for b in generics if removable(b)]
            # shown apart: their removal could not be written, the rest of the device still can
            unknown = [{"key": b["key"], "command": b["command"]} for b in generics if not removable(b)]
            device = found.setdefault(
                d["name"].lower(),
                {"device": spelling.get(d["name"].lower(), d["name"]), "name": name, "modules": []},
            )
            device["modules"].append(
                {
                    "profile": profile,
                    "unit_type": entry.get("unit_type"),
                    "file": d["name"],
                    "bindings": sorted(bindings, key=lambda b: (b["key"], b["command"])),
                    "unknown": sorted(unknown, key=lambda b: (b["key"], b["command"])),
                    "new_file": bool(d.get("extra")),
                    "error": t("bindings.path_too_long") if d.get("error") == PATH_TOO_LONG else None,
                }
            )
    return sorted(found.values(), key=lambda d: d["device"].lower())


def _signature(b: dict) -> tuple:
    return b["hash"], b["key"], tuple(sorted(b["reformers"]))


def remove_generic_buttons(
    install_dir: Path,
    saved_games_dir: Path,
    backups: BackupStore,
    devices: list[str],
    *,
    all_modules: bool = False,
    is_running: Callable[[], bool] = dcs_running,
    lua_interpreter=None,
) -> dict:
    """Removes the generic buttons of ``devices`` (names without GUID) in the scope, with one
    backup, then reads them again: ``{"backup", "written": [{"profile", "device", "removed",
    "expected", "deleted", "created"}], "differences": [text]}``."""
    chosen = plan(
        install_dir, saved_games_dir, devices, all_modules=all_modules, lua_interpreter=lua_interpreter
    )
    expected = {(m["profile"], m["file"].lower()): m for d in chosen for m in d["modules"] if not m["error"]}
    removals = [
        {
            "profile": m["profile"],
            "device": m["file"],
            "kind": "key",
            **{k: b[k] for k in ("hash", "key", "reformers")},
        }
        for m in expected.values()
        for b in m["bindings"]
    ]
    if not removals:
        raise DcsConfigError(t("generic.nothing"))
    count = len(chosen)
    reason = t("generic.reason.one" if count == 1 else "generic.reason.other", n=count)
    path = lambda r: input_dir_of(saved_games_dir) / r["profile"] / "joystick" / f"{r['device']}.diff.lua"  # noqa: E731
    existing = {(r["profile"], r["device"]): path(r).is_file() for r in removals}
    backup, rewrites = remove_bindings(
        install_dir,
        saved_games_dir,
        backups,
        removals,
        reason,
        is_running=is_running,
        lua_interpreter=lua_interpreter,
    )

    differences, written = [], []
    for r in rewrites:
        module = expected.get((r["profile"], r["device"].lower()))
        want = len(module["bindings"]) if module else 0
        written.append(
            {
                "profile": r["profile"],
                "device": r["device"],
                "removed": r["removed"],
                "expected": want,
                "deleted": r["written"] and r["diff"] is None,
                "created": r["written"]
                and r["diff"] is not None
                and not existing.get((r["profile"], r["device"])),
            }
        )
        if r["removed"] != want:
            differences.append(
                t(
                    "generic.other_count",
                    device=r["device"],
                    profile=r["profile"],
                    removed=r["removed"],
                    want=want,
                )
            )

    # read again: none of the buttons removed may still be there
    try:
        after = plan(
            install_dir, saved_games_dir, devices, all_modules=all_modules, lua_interpreter=lua_interpreter
        )
    except DcsConfigError as error:
        differences.append(t("bindings.read_again_failed", error=error))
        after = []
    for device in after:
        for m in device["modules"]:
            planned = expected.get((m["profile"], m["file"].lower()))
            before = {_signature(b) for b in planned["bindings"]} if planned else set()
            if left := sorted(b["key"] for b in m["bindings"] if _signature(b) in before):
                differences.append(
                    t("bindings.left_after", file=m["file"], profile=m["profile"], left=", ".join(left))
                )
    return {"backup": backup.as_dict(), "written": written, "differences": differences}
