"""Removing the 8 generic hat views ("View Up slow"…) in bulk.

Every module's joystick defaults include ``Config/Input/Aircrafts/common_joystick_binding.lua``,
which puts the slow views on the first hat of every device: on pedals, an ICP or MFDs, DCS
"has" a hat nobody touches. They are told apart by (command hash, key), the same in every module,
never by the displayed name (translated).

By default only the devices on whose hat the user placed nothing, in any module, are offered (the
diff files say what the user placed; a module's own defaults on a hat, such as a turret on
ground units, do not count). The ``every_device`` option offers every device; either way only
these 8 bindings go, and only where they come from the module's defaults: a view the user placed
stays. The scope is the profiles with a folder in ``Config/Input``, or, with
``all_modules``, every installed module (a diff is then created where the device has none).
Error messages reach the user as they are: they are in French."""

from collections.abc import Callable
from pathlib import Path

from .dcs_config import (
    BackupStore,
    DcsConfigError,
    dcs_running,
    device_diffs,
    disabled_devices,
    input_dir_of,
    remove_bindings,
    seen_devices,
)
from .engine import PATH_TOO_LONG, EffectiveBindingsError, load_effective_bindings
from .i18n import t

# key -> command hash of the 8 views in common_joystick_binding.lua (pressed = iCommandView…Slow,
# up = iCommandViewStop)
HAT_VIEWS = {
    "JOY_BTN_POV1_U": "dnilp34u214cdnilvdnilvpnilvunil",
    "JOY_BTN_POV1_D": "dnilp35u214cdnilvdnilvpnilvunil",
    "JOY_BTN_POV1_L": "dnilp32u214cdnilvdnilvpnilvunil",
    "JOY_BTN_POV1_R": "dnilp33u214cdnilvdnilvpnilvunil",
    "JOY_BTN_POV1_UL": "dnilp213u214cdnilvdnilvpnilvunil",
    "JOY_BTN_POV1_UR": "dnilp210u214cdnilvdnilvpnilvunil",
    "JOY_BTN_POV1_DL": "dnilp212u214cdnilvdnilvpnilvunil",
    "JOY_BTN_POV1_DR": "dnilp211u214cdnilvdnilvpnilvunil",
}
# shown, per device, of the hat bindings that are not these views
OWN_HAT_SHOWN = 6


def is_hat_view(binding: dict) -> bool:
    """One of the 8 views, as the module's defaults put it (not added by a diff)"""
    return (
        binding["kind"] == "key"
        and not binding.get("reformers")
        and not binding.get("from_diff")
        and HAT_VIEWS.get(binding["key"]) == binding["hash"]
    )


def _configured_profiles(saved_games_dir: Path) -> list[str]:
    try:
        return sorted(p.name for p in input_dir_of(saved_games_dir).iterdir() if p.is_dir())
    except OSError:
        return []


def _plugged_devices(saved_games_dir: Path, disabled: list[str]) -> list[str]:
    """The joysticks that may get a new diff: those DCS created at its last two starts, spelled as
    it logged them; without a log naming any, those with a diff somewhere. Disabled ones are left
    out. A device unplugged for good keeps its existing diffs and gets no new one."""
    spelling: dict[str, str] = {}
    for name in seen_devices(saved_games_dir):
        spelling.setdefault(name.lower(), name)
    if not spelling:
        for key, paths in device_diffs(saved_games_dir).items():
            spelling.setdefault(key, paths[0].name.removesuffix(".diff.lua"))
    skip = {d.lower() for d in disabled}
    return sorted((name for key, name in spelling.items() if key not in skip), key=str.lower)


def plan(
    install_dir: Path, saved_games_dir: Path, *, all_modules: bool = False, lua_interpreter=None
) -> list[dict]:
    """Devices whose hat carries some of the 8 views, in the profiles in scope: ``[{"device",
    "hat_only_views": the user placed nothing on its hat in any module, "own_hat": a few of the hat
    bindings the user placed, "own_hat_count", "modules": [{"profile", "unit_type", "file": the diff file's device name, "views":
    keys, "new_file": no diff there yet, "error"}]}]``."""
    disabled = disabled_devices(install_dir, saved_games_dir, lua_interpreter)
    extra = _plugged_devices(saved_games_dir, disabled)
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
    devices: dict[str, dict] = {}
    for profile, entry in sorted(result["profiles"].items()):
        if not entry.get("found"):
            continue
        for d in entry["devices"]:
            if d.get("source") != "effective":
                continue
            key = d["name"].lower()
            device = devices.setdefault(
                key,
                {"device": spelling.get(key, d["name"]), "own_hat": [], "own_hat_count": 0, "modules": []},
            )
            views = [b["key"] for b in d["bindings"] if is_hat_view(b)]
            for b in d["bindings"]:
                if "POV" in b["key"] and b.get("from_diff"):
                    device["own_hat_count"] += 1
                    if len(device["own_hat"]) < OWN_HAT_SHOWN:
                        device["own_hat"].append(
                            {"profile": profile, "key": b["key"], "command": b["command"]}
                        )
            if views:
                device["modules"].append(
                    {
                        "profile": profile,
                        "unit_type": entry.get("unit_type"),
                        "file": d["name"],
                        "views": sorted(views),
                        "new_file": bool(d.get("extra")),
                        "error": t("bindings.path_too_long") if d.get("error") == PATH_TOO_LONG else None,
                    }
                )
    out = []
    for device in devices.values():
        if device["modules"]:
            device["hat_only_views"] = device["own_hat_count"] == 0
            out.append(device)
    return sorted(out, key=lambda d: d["device"].lower())


def selectable(device: dict, every_device: bool) -> bool:
    return every_device or device["hat_only_views"]


def removals_of(devices: list[dict]) -> list[dict]:
    """The removals for ``remove_bindings``; modules in error are left out"""
    return [
        {"profile": m["profile"], "device": m["file"], "hash": HAT_VIEWS[key], "key": key}
        for device in devices
        for m in device["modules"]
        if not m["error"]
        for key in m["views"]
    ]


def remove_hat_views(
    install_dir: Path,
    saved_games_dir: Path,
    backups: BackupStore,
    devices: list[str],
    *,
    every_device: bool = False,
    all_modules: bool = False,
    is_running: Callable[[], bool] = dcs_running,
    lua_interpreter=None,
) -> dict:
    """Removes the 8 views from ``devices`` (full names) in the scope, with one backup, then reads
    the bindings again: ``{"backup", "written": [{"profile", "device", "removed", "expected",
    "deleted", "created"}], "differences": [text]}``; a difference is a view still there or a count
    other than the preview's."""
    wanted = {d.lower() for d in devices}
    chosen = [
        d
        for d in plan(install_dir, saved_games_dir, all_modules=all_modules, lua_interpreter=lua_interpreter)
        if d["device"].lower() in wanted and selectable(d, every_device)
    ]
    removals = removals_of(chosen)
    if not removals:
        raise DcsConfigError(t("hat.nothing"))
    expected = {(m["profile"], m["file"].lower()): m for d in chosen for m in d["modules"] if not m["error"]}
    count = len(chosen)
    reason = t("hat.reason.one" if count == 1 else "hat.reason.other", n=count)
    existing = {(r["profile"], r["device"]): _diff_path(saved_games_dir, r).is_file() for r in removals}
    backup, rewrites = remove_bindings(
        install_dir,
        saved_games_dir,
        backups,
        removals,
        reason,
        is_running=is_running,
        lua_interpreter=lua_interpreter,
    )

    differences = []
    written = []
    for r in rewrites:
        module = expected.get((r["profile"], r["device"].lower()))
        want = len(module["views"]) if module else 0
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
                    "hat.other_count",
                    device=r["device"],
                    profile=r["profile"],
                    removed=r["removed"],
                    want=want,
                )
            )

    # read again: none of the views removed may still be there
    try:
        after = plan(install_dir, saved_games_dir, all_modules=all_modules, lua_interpreter=lua_interpreter)
    except DcsConfigError as error:
        differences.append(t("bindings.read_again_failed", error=error))
        after = []
    for device in after:
        for m in device["modules"]:
            planned = expected.get((m["profile"], m["file"].lower()))
            if left := sorted(set(m["views"]) & set(planned["views"] if planned else [])):
                differences.append(
                    t("bindings.left_after", file=m["file"], profile=m["profile"], left=", ".join(left))
                )
    return {"backup": backup.as_dict(), "written": written, "differences": differences}


def _diff_path(saved_games_dir: Path, removal: dict) -> Path:
    return input_dir_of(saved_games_dir) / removal["profile"] / "joystick" / f"{removal['device']}.diff.lua"
