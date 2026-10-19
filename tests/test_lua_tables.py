import shutil
from pathlib import Path

import pytest

from hotas_kneeboard.dcs_config import (
    BackupNotFoundError,
    BackupStore,
    DcsConfigError,
    deleted_modifiers,
    disabled_devices,
    fix_modifiers,
    modifier_issues,
    read_disabled,
    restore_modifiers,
    seen_devices,
    set_device_disabled,
)
from hotas_kneeboard.lua_tables import read_table, to_lua, write_table

from .test_engine import INSTALL, SAVED_GAMES, find_lua51

DISABLED = SAVED_GAMES / "Config" / "Input" / "disabled.lua"
GHOST = "Ghost Pad {AAAA0000-0000-11ef-8001-444553540000}"
# a value shaped like a real diff: nested lists, numbers, booleans, a key needing escapes
SAMPLE = {
    "axisDiffs": {
        "a2001cdnil": {
            "changed": [
                {
                    "filter": {"curvature": [0.1], "deadzone": 0, "invert": False, "slider": True},
                    "key": "JOY_Y",
                }
            ],
            "name": 'Roll "fast" \\ é\n',
        }
    },
    "keyDiffs": {
        "d1054pnilu1054cd": {"name": "Gear", "removed": [{"key": "JOY_BTN21", "reformers": ["JOY_BTN4"]}]}
    },
}


@pytest.fixture(scope="module")
def lua():
    interpreter = find_lua51()
    if not interpreter:
        pytest.skip("no Lua 5.1 interpreter (set DCS_TEST_LUA)")
    return interpreter


def real_install(lua: str) -> Path | None:
    """The DCS install of DCS_TEST_LUA when it is bin/luae.exe of a real one"""
    install = Path(lua).parent.parent
    return install if (install / "Scripts" / "Serializer.lua").is_file() and install != INSTALL else None


def test_a_file_written_as_dcs_reads_back_identical(lua, tmp_path):
    out = tmp_path / "x.diff.lua"
    write_table(INSTALL, out, "diff", SAMPLE, lua)
    assert read_table(INSTALL, out, lua) == SAMPLE
    assert out.read_bytes().endswith(b"}\nreturn diff")
    assert b"\r" not in out.read_bytes()


def test_a_dcs_file_is_rewritten_byte_for_byte(lua, tmp_path):
    out = tmp_path / "disabled.lua"
    write_table(INSTALL, out, "disabled", read_table(INSTALL, DISABLED, lua), lua)
    assert out.read_bytes() == DISABLED.read_bytes()


def test_the_test_serializer_writes_what_dcs_writes(lua, tmp_path):
    install = real_install(lua)
    if not install:
        pytest.skip("no DCS install (DCS_TEST_LUA = <DCS>/bin/luae.exe)")
    write_table(install, tmp_path / "dcs.lua", "diff", SAMPLE, lua)
    write_table(INSTALL, tmp_path / "standin.lua", "diff", SAMPLE, lua)
    assert (tmp_path / "dcs.lua").read_bytes() == (tmp_path / "standin.lua").read_bytes()


def test_lua_source_is_plain_ascii():
    source = to_lua({"k": 'é\r\x1a"\\'})
    assert source.isascii()
    assert "\r" not in source and "\x1a" not in source


@pytest.fixture
def saved(tmp_path):
    copy = tmp_path / "Saved Games" / "DCS"
    shutil.copytree(SAVED_GAMES, copy)
    return copy


def closed():
    return False


def test_disable_and_enable_a_device(lua, saved, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    stick = "Fake Stick {84180FE0-BDD3-11ea-8001-444553540000}"
    set_device_disabled(INSTALL, saved, backups, stick, True, is_running=closed, lua_interpreter=lua)
    assert disabled_devices(INSTALL, saved, lua) == sorted([GHOST, stick])
    assert read_disabled(INSTALL, saved, lua)["pnp"] is False

    set_device_disabled(INSTALL, saved, backups, GHOST, False, is_running=closed, lua_interpreter=lua)
    assert disabled_devices(INSTALL, saved, lua) == [stick]
    assert [b.reason for b in backups.list()] == [
        f"avant la réactivation de {GHOST}",
        f"avant la désactivation de {stick}",
    ]


def test_the_device_takes_the_spelling_dcs_logged(lua, saved, tmp_path):
    (saved / "Logs").mkdir()
    logged = "Fake Stick {84180fe0-bdd3-11ea-8001-444553540000}"
    (saved / "Logs" / "dcs.log").write_text(
        f"2026-10-18 16:42:54.566 INFO    INPUT (Main): created [Fake Stick] with full id [{logged}],JOYSTICK|STANDARD\n",
        encoding="utf-8",
    )
    assert seen_devices(saved) == [logged]
    backups = BackupStore(tmp_path / "backups")
    set_device_disabled(INSTALL, saved, backups, logged.upper(), True, is_running=closed, lua_interpreter=lua)
    assert logged in disabled_devices(INSTALL, saved, lua)


def test_nothing_is_disabled_while_dcs_runs(lua, saved, tmp_path):
    before = DISABLED.read_bytes()
    with pytest.raises(DcsConfigError, match="DCS est lancé"):
        set_device_disabled(
            INSTALL,
            saved,
            BackupStore(tmp_path / "b"),
            GHOST,
            False,
            is_running=lambda: True,
            lua_interpreter=lua,
        )
    assert (saved / "Config" / "Input" / "disabled.lua").read_bytes() == before


def test_a_device_keeps_the_spelling_disabled_lua_uses(lua, saved, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    set_device_disabled(INSTALL, saved, backups, GHOST.upper(), True, is_running=closed, lua_interpreter=lua)
    assert disabled_devices(INSTALL, saved, lua) == [GHOST]


@pytest.fixture
def make_client(lua, saved, tmp_path):
    from fastapi.testclient import TestClient

    from hotas_kneeboard.app import create_app
    from hotas_kneeboard.settings import Settings, SettingsStore
    from hotas_kneeboard.templates import TemplateLibrary

    def make(running=False):
        store = SettingsStore(tmp_path / "data" / "settings.json")
        store.save(Settings(dcs_install_dir=str(INSTALL), saved_games_dir=str(saved)))
        app = create_app(
            store,
            TemplateLibrary([tmp_path / "templates"], user_dir=tmp_path / "user"),
            lua_interpreter=lua,
            backups=BackupStore(tmp_path / "backups"),
            is_dcs_running=lambda: running,
        )
        return TestClient(app, base_url="http://127.0.0.1:8642")

    return make


def test_the_api_disables_a_device_and_the_pages_say_so(make_client):
    client = make_client()
    stick = "Fake Stick {84180FE0-BDD3-11ea-8001-444553540000}"
    assert client.get("/api/dcs-config/devices").json()["disabled"] == [GHOST]
    client.get("/api/bindings")  # fills the cache, which the change must invalidate
    response = client.put("/api/dcs-config/devices/disabled", json={"device": stick, "disabled": True})
    assert response.status_code == 200
    assert client.get("/api/dcs-config/devices").json()["disabled"] == sorted([GHOST, stick])
    fake = next(p for p in client.get("/api/bindings").json()["profiles"] if p["name"] == "FakePlane")
    assert next(d for d in fake["devices"] if d["full_name"] == stick)["dcs_disabled"] is True


def test_the_api_refuses_to_disable_while_dcs_runs(make_client, saved):
    before = (saved / "Config" / "Input" / "disabled.lua").read_bytes()
    response = make_client(running=True).put(
        "/api/dcs-config/devices/disabled", json={"device": GHOST, "disabled": False}
    )
    assert response.status_code == 409
    assert (saved / "Config" / "Input" / "disabled.lua").read_bytes() == before


STICK = "Fake Stick {84180FE0-BDD3-11ea-8001-444553540000}"
THROTTLE = "Fake Throttle {84180FE0-BDD3-11ea-8002-444553540000}"
SENSOR_UP = "d3004pnilunilcd13vd1vpnilvunil"
MASTER_ARM = "d3003pnilunilcd12vd1vpnilvunil"


def key_bindings(saved, lua, device):
    from hotas_kneeboard.engine import load_effective_bindings

    result = load_effective_bindings(INSTALL, saved, ["FakePlane"], lua)
    found = next(d for d in result["profiles"]["FakePlane"]["devices"] if d["name"] == device)
    return {(b["hash"], b["key"], tuple(b["reformers"])) for b in found["bindings"] if b["kind"] == "key"}


def remove(saved, tmp_path, lua, device, removals):
    from hotas_kneeboard.dcs_config import remove_bindings

    full = [{"profile": "FakePlane", "device": device, **r} for r in removals]
    return remove_bindings(
        INSTALL,
        saved,
        BackupStore(tmp_path / "backups"),
        full,
        "essai",
        is_running=closed,
        lua_interpreter=lua,
    )


def test_removing_a_default_binding_writes_a_removed_entry(lua, saved, tmp_path):
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{STICK}.diff.lua"
    before, bindings = read_table(INSTALL, path, lua), key_bindings(saved, lua, STICK)
    remove(saved, tmp_path, lua, STICK, [{"hash": SENSOR_UP, "key": "JOY_BTN_POV1_U"}])
    after = read_table(INSTALL, path, lua)
    assert after["keyDiffs"][SENSOR_UP] == {"name": "Sensor Up", "removed": [{"key": "JOY_BTN_POV1_U"}]}
    assert {k: v for k, v in after["keyDiffs"].items() if k != SENSOR_UP} == before["keyDiffs"]
    assert after["axisDiffs"] == before["axisDiffs"]
    assert key_bindings(saved, lua, STICK) == bindings - {(SENSOR_UP, "JOY_BTN_POV1_U", ())}


def test_removing_a_binding_the_user_added_drops_its_entry(lua, saved, tmp_path):
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{STICK}.diff.lua"
    remove(saved, tmp_path, lua, STICK, [{"hash": MASTER_ARM, "key": "JOY_BTN4", "reformers": ["JOY_BTN5"]}])
    assert MASTER_ARM not in read_table(INSTALL, path, lua)["keyDiffs"]
    assert (MASTER_ARM, "JOY_BTN4", ("JOY_BTN5",)) not in key_bindings(saved, lua, STICK)


ZOOM = "a2001cd14"  # JOY_Y by default, its filter changed by the user
BRIGHTNESS = "a2002cd14"  # JOY_Z by default, untouched


def axis_bindings(saved, lua, device):
    from hotas_kneeboard.engine import load_effective_bindings

    result = load_effective_bindings(INSTALL, saved, ["FakePlane"], lua)
    found = next(d for d in result["profiles"]["FakePlane"]["devices"] if d["name"] == device)
    return {(b["hash"], b["key"]) for b in found["bindings"] if b["kind"] == "axis"}


def test_removing_a_default_axis_writes_a_removed_entry(lua, saved, tmp_path):
    # the throttle keeps the module's axes as they are: Brightness on JOY_Z
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{THROTTLE}.diff.lua"
    before, axes = read_table(INSTALL, path, lua), axis_bindings(saved, lua, THROTTLE)
    assert (BRIGHTNESS, "JOY_Z") in axes and "axisDiffs" not in before
    _, rewrites = remove(
        saved, tmp_path, lua, THROTTLE, [{"hash": BRIGHTNESS, "key": "JOY_Z", "kind": "axis"}]
    )
    assert rewrites[0]["removed"] == 1
    after = read_table(INSTALL, path, lua)
    assert after["axisDiffs"] == {BRIGHTNESS: {"name": "Brightness", "removed": [{"key": "JOY_Z"}]}}
    assert after["keyDiffs"] == before["keyDiffs"]
    assert axis_bindings(saved, lua, THROTTLE) == axes - {(BRIGHTNESS, "JOY_Z")}


def test_removing_an_axis_whose_filter_was_changed(lua, saved, tmp_path):
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{STICK}.diff.lua"
    remove(saved, tmp_path, lua, STICK, [{"hash": ZOOM, "key": "JOY_Y", "kind": "axis"}])
    # a default combo removed: DCS writes it removed, its changed filter goes with it
    assert read_table(INSTALL, path, lua)["axisDiffs"][ZOOM] == {
        "name": "Zoom",
        "removed": [{"key": "JOY_Y"}],
    }
    assert (ZOOM, "JOY_Y") not in axis_bindings(saved, lua, STICK)


def test_a_key_removal_does_not_take_an_axis_of_the_same_key(lua, saved, tmp_path):
    # without its kind, the removal of JOY_Z is a key one: no key command has it, nothing is written
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{THROTTLE}.diff.lua"
    before = path.read_bytes()
    _, rewrites = remove(saved, tmp_path, lua, THROTTLE, [{"hash": BRIGHTNESS, "key": "JOY_Z"}])
    assert rewrites[0]["removed"] == 0 and rewrites[0]["written"] is False
    assert path.read_bytes() == before


def test_without_a_user_diff_the_module_diff_is_copied_in(lua, saved, tmp_path):
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{THROTTLE}.diff.lua"
    path.unlink()
    shipped = read_table(
        INSTALL, INSTALL / "Mods/aircraft/FakePlane/Input/FakePlane/joystick/Fake Throttle.diff.lua", lua
    )
    remove(saved, tmp_path, lua, THROTTLE, [{"hash": SENSOR_UP, "key": "JOY_BTN_POV1_U"}])
    written = read_table(INSTALL, path, lua)
    assert written["keyDiffs"][SENSOR_UP]["removed"] == [{"key": "JOY_BTN_POV1_U"}]
    for part in ("axisDiffs", "ffDiffs"):
        assert written.get(part) == shipped.get(part)


def test_an_error_on_one_device_writes_nothing(lua, saved, tmp_path):
    stick = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{STICK}.diff.lua"
    before = stick.read_bytes()
    with pytest.raises(DcsConfigError):
        from hotas_kneeboard.dcs_config import remove_bindings

        remove_bindings(
            INSTALL,
            saved,
            BackupStore(tmp_path / "backups"),
            [
                {"profile": "FakePlane", "device": STICK, "hash": SENSOR_UP, "key": "JOY_BTN_POV1_U"},
                {"profile": "NotAModule", "device": STICK, "hash": SENSOR_UP, "key": "JOY_BTN_POV1_U"},
            ],
            "essai",
            is_running=closed,
            lua_interpreter=lua,
        )
    assert stick.read_bytes() == before


def test_an_entry_no_command_has_is_dropped_as_dcs_does(lua, saved, tmp_path):
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{STICK}.diff.lua"
    diff = read_table(INSTALL, path, lua)
    diff["keyDiffs"]["d9999pnilunilcd12vd1vpnilvunil"] = {"name": "Gone", "added": [{"key": "JOY_BTN30"}]}
    write_table(INSTALL, path, "diff", diff, lua)
    remove(saved, tmp_path, lua, STICK, [{"hash": SENSOR_UP, "key": "JOY_BTN_POV1_U"}])
    assert "d9999pnilunilcd12vd1vpnilvunil" not in read_table(INSTALL, path, lua)["keyDiffs"]


def test_a_device_name_with_a_comma_is_accepted(lua):
    from hotas_kneeboard.engine import _loader_input

    data = _loader_input(
        "i", "s", ["P"], [{"profile": "P", "device": "Pedals, USB {1}", "hash": "h", "key": "K"}]
    )
    assert b"remove\tP\tPedals, USB {1}\th\tK\t\tkey\n" in data


def test_axis_entries_are_recomputed_as_dcs_does(lua, saved, tmp_path):
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{STICK}.diff.lua"
    diff = read_table(INSTALL, path, lua)
    kept = dict(diff["axisDiffs"])
    # an axis the defaults do not bind: removing it changes nothing, DCS writes no entry for it
    diff["axisDiffs"]["a2099cd14"] = {"name": "Gone axis", "removed": [{"key": "JOY_SLIDER1"}]}
    write_table(INSTALL, path, "diff", diff, lua)
    remove(saved, tmp_path, lua, STICK, [{"hash": SENSOR_UP, "key": "JOY_BTN_POV1_U"}])
    assert read_table(INSTALL, path, lua)["axisDiffs"] == kept


def test_a_user_diff_the_interpreter_could_not_read_stops_everything(monkeypatch, saved, tmp_path):
    from hotas_kneeboard import dcs_config

    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{STICK}.diff.lua"
    before = path.read_bytes()
    rewrite = {
        "profile": "FakePlane",
        "device": STICK,
        "diff": {"keyDiffs": {}, "axisDiffs": {}, "source": None},
    }
    monkeypatch.setattr(dcs_config, "load_effective_bindings", lambda *a, **k: {"rewrites": [rewrite]})
    with pytest.raises(DcsConfigError, match="illisible"):
        dcs_config.remove_bindings(
            INSTALL,
            saved,
            BackupStore(tmp_path / "backups"),
            [{"profile": "FakePlane", "device": STICK, "hash": SENSOR_UP, "key": "JOY_BTN_POV1_U"}],
            "essai",
            is_running=closed,
        )
    assert path.read_bytes() == before


def test_an_axis_filter_is_written_only_when_it_differs(lua, saved, tmp_path):
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{STICK}.diff.lua"
    diff = read_table(INSTALL, path, lua)
    default = {
        "curvature": [0],
        "deadzone": 0,
        "invert": False,
        "saturationX": 1,
        "saturationY": 1,
        "slider": False,
    }
    # the default axis of "Zoom" (JOY_Y) given back its default filter: no "changed" entry any more
    diff["axisDiffs"]["a2001cd14"]["changed"][0]["filter"] = default
    write_table(INSTALL, path, "diff", diff, lua)
    remove(saved, tmp_path, lua, STICK, [{"hash": SENSOR_UP, "key": "JOY_BTN_POV1_U"}])
    assert "a2001cd14" not in read_table(INSTALL, path, lua)["axisDiffs"]


def test_a_too_long_diff_path_is_flagged_on_the_page(monkeypatch):
    from hotas_kneeboard import engine

    monkeypatch.setattr(engine.sys, "platform", "win32")
    result = {"profiles": {"P": {"devices": [{"name": "D" * 300, "error": None}]}}}
    engine._flag_long_paths(result, Path("C:/Saved Games/DCS"))
    assert result["profiles"]["P"]["devices"][0]["error"] == engine.PATH_TOO_LONG


# --- modifiers on a renamed device ---------------------------------------------------------------

OLD_STICK = "Old Stick {84180FE0-BDD3-11ea-8001-444553540000}"
LOGGED_STICK = "Fake Stick {84180fe0-bdd3-11ea-8001-444553540000}"
KEYBOARD_SHIFT = {"device": "Keyboard", "key": "LShift", "switch": False}


def modifiers_of(device):
    # JOY_BTN5: the reformer the fixture's stick and throttle bindings use
    return {
        "JOY_BTN5": {"device": device, "key": "JOY_BTN5", "switch": False},
        "LShift": dict(KEYBOARD_SHIFT),
    }


def log_devices(saved, *devices):
    (saved / "Logs").mkdir(exist_ok=True)
    lines = [f"INFO    INPUT (Main): created [x] with full id [{d}],JOYSTICK|STANDARD" for d in devices]
    (saved / "Logs" / "dcs.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def renamed(lua, saved):
    """FakePlane's JOY_BTN5 modifier on the stick's old name; DCS logged its new one"""
    write_table(
        INSTALL,
        saved / "Config" / "Input" / "FakePlane" / "modifiers.lua",
        "modifiers",
        modifiers_of(OLD_STICK),
        lua,
    )
    log_devices(saved, LOGGED_STICK, THROTTLE)
    return saved / "Config" / "Input" / "FakePlane" / "modifiers.lua"


def test_a_modifier_on_a_renamed_device_is_found(lua, saved, renamed):
    assert modifier_issues(INSTALL, saved, lua) == [
        {
            "profile": "FakePlane",
            "modifier": "JOY_BTN5",
            "key": "JOY_BTN5",
            "device": OLD_STICK,
            "new_device": LOGGED_STICK,
            "problem": None,
        }
    ]


def test_a_guid_of_another_case_is_a_rename_too(lua, saved, renamed):
    # DCS compares the strings: "11EA" in the file, "11ea" in the log drops the modifier
    write_table(INSTALL, renamed, "modifiers", modifiers_of(LOGGED_STICK.upper()), lua)
    assert [i["new_device"] for i in modifier_issues(INSTALL, saved, lua)] == [LOGGED_STICK]


def test_an_unplugged_device_is_not_a_rename(lua, saved, renamed):
    log_devices(saved, THROTTLE)
    assert modifier_issues(INSTALL, saved, lua) == []
    with pytest.raises(DcsConfigError, match="Aucun modificateur"):
        fix_modifiers(INSTALL, saved, BackupStore(saved.parent / "b"), is_running=closed, lua_interpreter=lua)


def test_right_after_a_rename_the_last_session_wins(lua, saved, renamed):
    # first launch after the driver update: dcs.log.old still has the old name, dcs.log the new one
    (saved / "Logs" / "dcs.log").replace(saved / "Logs" / "dcs.log.old")
    (saved / "Logs" / "dcs.log.old").write_text(
        f"INFO    INPUT (Main): created [x] with full id [{OLD_STICK}],JOYSTICK|STANDARD\n", encoding="utf-8"
    )
    log_devices(saved, LOGGED_STICK)
    assert [i["new_device"] for i in modifier_issues(INSTALL, saved, lua)] == [LOGGED_STICK]


def test_an_unreadable_file_does_not_stop_the_others(lua, saved, renamed, tmp_path):
    broken = saved / "Config" / "Input" / "SecondPlane_pilot" / "modifiers.lua"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("not lua at all {", encoding="utf-8")
    _, fixed = fix_modifiers(
        INSTALL, saved, BackupStore(tmp_path / "b"), is_running=closed, lua_interpreter=lua
    )
    assert [f["profile"] for f in fixed] == ["FakePlane"]
    assert broken.read_text(encoding="utf-8") == "not lua at all {"


def test_two_names_for_one_guid_are_refused(lua, saved, renamed):
    log_devices(saved, LOGGED_STICK, "Other Stick {84180FE0-BDD3-11EA-8001-444553540000}")
    [issue] = modifier_issues(INSTALL, saved, lua)
    assert issue["new_device"] is None and "plusieurs" in issue["problem"]


def test_fixing_writes_the_logged_name_as_dcs_writes_it(lua, saved, renamed, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    backup, fixed = fix_modifiers(INSTALL, saved, backups, is_running=closed, lua_interpreter=lua)
    assert fixed == [
        {"profile": "FakePlane", "modifier": "JOY_BTN5", "device": OLD_STICK, "new_device": LOGGED_STICK}
    ]
    write_table(INSTALL, tmp_path / "expected.lua", "modifiers", modifiers_of(LOGGED_STICK), lua)
    assert renamed.read_bytes() == (tmp_path / "expected.lua").read_bytes()
    assert renamed.read_bytes().endswith(b"}\nreturn modifiers")
    assert backup.reason == "avant la réparation des modificateurs"
    assert modifier_issues(INSTALL, saved, lua) == []


def test_nothing_is_fixed_while_dcs_runs(lua, saved, renamed, tmp_path):
    before = renamed.read_bytes()
    with pytest.raises(DcsConfigError, match="DCS est lancé"):
        fix_modifiers(
            INSTALL, saved, BackupStore(tmp_path / "b"), is_running=lambda: True, lua_interpreter=lua
        )
    assert renamed.read_bytes() == before


def test_a_deleted_modifiers_file_comes_back_renamed(lua, saved, renamed, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    taken = backups.create(saved / "Config" / "Input", "avant essai")
    renamed.unlink()  # what DCS does when a dropped modifier leaves only the defaults
    assert deleted_modifiers(saved, backups) == [
        {"profile": "FakePlane", "backup": taken.id, "created": taken.created.isoformat(timespec="seconds")}
    ]
    backup, fixed = restore_modifiers(
        INSTALL, saved, backups, "FakePlane", taken.id, is_running=closed, lua_interpreter=lua
    )
    assert [f["new_device"] for f in fixed] == [LOGGED_STICK]
    assert read_table(INSTALL, renamed, lua) == modifiers_of(LOGGED_STICK)
    assert backup.reason == "avant de ramener modifiers.lua de FakePlane"
    assert deleted_modifiers(saved, backups) == []
    with pytest.raises(DcsConfigError, match="déjà"):
        restore_modifiers(
            INSTALL, saved, backups, "FakePlane", taken.id, is_running=closed, lua_interpreter=lua
        )


def test_a_keyboard_only_file_is_not_offered_back(lua, saved, tmp_path):
    path = saved / "Config" / "Input" / "FakePlane" / "modifiers.lua"
    write_table(INSTALL, path, "modifiers", {"LShift": dict(KEYBOARD_SHIFT)}, lua)
    backups = BackupStore(tmp_path / "backups")
    backups.create(saved / "Config" / "Input", "avant essai")
    path.unlink()
    assert deleted_modifiers(saved, backups) == []


def test_a_profile_outside_config_input_is_refused(lua, saved, renamed, tmp_path):
    backups = BackupStore(tmp_path / "backups")
    taken = backups.create(saved / "Config" / "Input", "avant essai")
    with pytest.raises(BackupNotFoundError):
        restore_modifiers(INSTALL, saved, backups, "..", taken.id, is_running=closed, lua_interpreter=lua)


def test_the_api_lists_fixes_and_flags_the_pages(make_client, renamed):
    client = make_client()
    fake = next(p for p in client.get("/api/bindings").json()["profiles"] if p["name"] == "FakePlane")
    assert {d["full_name"]: d["inactive_modifiers"] for d in fake["devices"]}[STICK] == ["JOY_BTN5"]
    assert [i["profile"] for i in client.get("/api/dcs-config/modifiers").json()["issues"]] == ["FakePlane"]

    assert make_client(running=True).post("/api/dcs-config/modifiers/fix").status_code == 409
    response = client.post("/api/dcs-config/modifiers/fix")
    assert response.status_code == 200 and len(response.json()["fixed"]) == 1
    assert client.get("/api/dcs-config/modifiers").json()["issues"] == []
    fake = next(p for p in client.get("/api/bindings").json()["profiles"] if p["name"] == "FakePlane")
    assert all(d["inactive_modifiers"] == [] for d in fake["devices"])


def test_the_api_brings_a_modifiers_file_back(make_client, saved, renamed):
    client = make_client()
    taken = client.post("/api/dcs-config/backups").json()
    renamed.unlink()
    [offer] = client.get("/api/dcs-config/modifiers").json()["deleted"]
    assert offer["backup"] == taken["id"]
    body = {"profile": "FakePlane", "backup": "20200101-000000-000000"}
    assert client.post("/api/dcs-config/modifiers/restore", json=body).status_code == 404
    response = client.post(
        "/api/dcs-config/modifiers/restore", json={"profile": "FakePlane", "backup": taken["id"]}
    )
    assert response.status_code == 200
    assert renamed.is_file()


def device_rows(client, device):
    response = client.get("/api/dcs-config/bindings", params={"profile": "FakePlane", "device": device})
    assert response.status_code == 200
    return response.json()


def test_the_api_lists_a_device_bindings_with_their_origin(make_client):
    data = device_rows(make_client(), THROTTLE)
    assert data["editable"] is True
    rows = {(b["kind"], b["key"], tuple(b["reformers"])): b for b in data["bindings"]}
    assert rows[("axis", "JOY_Z", ())]["command"] == "Brightness"
    # the module has a profile for the throttle (Fake Throttle.lua)
    assert rows[("axis", "JOY_Z", ())]["origin"] == "device"
    # placed by the user's diff
    assert rows[("key", "JOY_BTN10", ("JOY_BTN5",))]["origin"] == "user"
    # none for the stick: what DCS puts on it comes from the profile of any joystick
    stick = {
        (b["kind"], b["key"], tuple(b["reformers"])): b for b in device_rows(make_client(), STICK)["bindings"]
    }
    assert stick[("key", "JOY_BTN_POV1_U", ())]["origin"] == "generic"
    # an engine command whose number is unknown: listed, not removable
    assert stick[("key", "JOY_BTN_POV1_U", ())]["removable"] is True
    assert stick[("key", "JOY_BTN7", ())]["removable"] is False


def test_a_binding_the_module_ships_for_the_device_is_not_the_user_s(lua, saved):
    # DCS copies the module's diff into the user's at the first save: its Trim on JOY_BTN11 stays
    # the module's
    from hotas_kneeboard.engine import load_effective_bindings

    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{THROTTLE}.diff.lua"
    diff = read_table(INSTALL, path, lua)
    diff["keyDiffs"]["dnilp100unilcdnilvdnilvpnilvunil"] = {
        "name": "Trim: Nose Up",
        "added": [{"key": "JOY_BTN11"}],
    }
    write_table(INSTALL, path, "diff", diff, lua)
    result = load_effective_bindings(INSTALL, saved, ["FakePlane"], lua)
    throttle = next(d for d in result["profiles"]["FakePlane"]["devices"] if d["name"] == THROTTLE)
    trim = next(b for b in throttle["bindings"] if b["key"] == "JOY_BTN11")
    assert not trim.get("from_diff") and trim.get("from_module_diff")
    brake = next(b for b in throttle["bindings"] if b["key"] == "JOY_BTN10" and b["reformers"])
    assert brake.get("from_diff") and not brake.get("from_module_diff")


def test_the_api_removes_a_key_and_an_axis_then_the_backup_gives_them_back(make_client, saved):
    client = make_client()
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{THROTTLE}.diff.lua"
    before = path.read_bytes()
    client.get("/api/bindings")  # fills the cache, which the removal must invalidate
    response = client.post(
        "/api/dcs-config/bindings/remove",
        json={
            "profile": "FakePlane",
            "device": THROTTLE,
            "bindings": [
                {"kind": "axis", "hash": BRIGHTNESS, "key": "JOY_Z"},
                {
                    "kind": "key",
                    "hash": "d3010pnilunilcd15vd1vpnilvunil",
                    "key": "JOY_BTN10",
                    "reformers": ["JOY_BTN5"],
                },
            ],
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert (result["removed"], result["asked"]) == (2, 2)
    keys = {(b["kind"], b["key"], tuple(b["reformers"])) for b in device_rows(client, THROTTLE)["bindings"]}
    assert ("axis", "JOY_Z", ()) not in keys and ("key", "JOY_BTN10", ("JOY_BTN5",)) not in keys
    # Speed Brake keeps its default on JOY_BTN10, without the modifier
    assert ("key", "JOY_BTN10", ()) in keys
    fake = next(p for p in client.get("/api/bindings").json()["profiles"] if p["name"] == "FakePlane")
    throttle = next(d for d in fake["devices"] if d["full_name"] == THROTTLE)
    assert "JOY_Z" not in throttle["inputs"]
    # Annuler: the backup made before the removal
    restored = client.post(f"/api/dcs-config/backups/{result['backup']['id']}/restore")
    assert restored.status_code == 200
    assert path.read_bytes() == before


def test_the_api_refuses_to_remove_while_dcs_runs(make_client, saved):
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{THROTTLE}.diff.lua"
    before = path.read_bytes()
    response = make_client(running=True).post(
        "/api/dcs-config/bindings/remove",
        json={
            "profile": "FakePlane",
            "device": THROTTLE,
            "bindings": [{"kind": "axis", "hash": BRIGHTNESS, "key": "JOY_Z"}],
        },
    )
    assert response.status_code == 409
    assert path.read_bytes() == before


def test_generic_buttons_of_a_device_without_any(lua, saved):
    from hotas_kneeboard.generic_buttons import plan

    devices = plan(INSTALL, saved, ["Fake Stick", "Fake Throttle"], lua_interpreter=lua)
    # the throttle has a profile of its own in the module: nothing generic on it
    assert [d["name"] for d in devices] == ["Fake Stick"]
    keys = {(b["key"], tuple(b["reformers"])) for m in devices[0]["modules"] for b in m["bindings"]}
    assert ("JOY_BTN_POV1_U", ()) in keys
    # placed by the user: stays
    assert ("JOY_BTN4", ("JOY_BTN5",)) not in keys
    # an engine command whose number is unknown: not offered, its removal could not be written
    assert ("JOY_BTN7", ()) not in keys
    assert {b["key"] for m in devices[0]["modules"] for b in m["unknown"]} == {"JOY_BTN7"}


def test_removing_the_generic_buttons_keeps_the_user_s_and_the_axes(lua, saved, tmp_path):
    from hotas_kneeboard.generic_buttons import remove_generic_buttons

    axes = axis_bindings(saved, lua, STICK)
    result = remove_generic_buttons(
        INSTALL,
        saved,
        BackupStore(tmp_path / "backups"),
        ["fake stick"],
        is_running=closed,
        lua_interpreter=lua,
    )
    assert result["differences"] == []
    left = key_bindings(saved, lua, STICK)
    assert (MASTER_ARM, "JOY_BTN4", ("JOY_BTN5",)) in left
    assert (SENSOR_UP, "JOY_BTN_POV1_U", ()) not in left
    assert axis_bindings(saved, lua, STICK) == axes


def test_the_api_previews_then_removes_the_generic_buttons(make_client, saved):
    client = make_client()
    path = saved / "Config" / "Input" / "FakePlane" / "joystick" / f"{STICK}.diff.lua"
    before = path.read_bytes()
    assert client.get("/api/dcs-config/generic-buttons").json()["devices"] == []  # nothing marked yet
    assert client.put("/api/settings", json={"buttonless_devices": ["Fake Stick"]}).status_code == 200
    preview = client.get("/api/dcs-config/generic-buttons").json()
    assert [d["name"] for d in preview["devices"]] == ["Fake Stick"]
    response = client.post("/api/dcs-config/generic-buttons", json={})
    assert response.status_code == 200 and response.json()["differences"] == []
    # nothing removable left; the one whose engine command is unknown stays, shown apart
    after = client.get("/api/dcs-config/generic-buttons").json()["devices"]
    assert [b for d in after for m in d["modules"] for b in m["bindings"]] == []
    assert {b["key"] for d in after for m in d["modules"] for b in m["unknown"]} == {"JOY_BTN7"}
    restored = client.post(f"/api/dcs-config/backups/{response.json()['backup']['id']}/restore")
    assert restored.status_code == 200 and path.read_bytes() == before


def test_every_installed_module_reaches_where_the_device_has_no_diff(lua, saved):
    from hotas_kneeboard.generic_buttons import plan

    devices = plan(INSTALL, saved, ["Fake Throttle"], all_modules=True, lua_interpreter=lua)
    modules = {m["profile"]: m["new_file"] for d in devices for m in d["modules"]}
    # no profile for the throttle in these modules: the profile of any joystick, a new diff
    assert modules.get("CommunityPlane") is True
