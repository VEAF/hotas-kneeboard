import struct

from hotas_kneeboard.dcs import command_translator, resolve_dirs

from .test_engine import INSTALL, SAVED_GAMES


def write_mo(path, messages: dict[str, str]) -> None:
    """Minimal GNU .mo file (what DCS ships in l10n/<language>/LC_MESSAGES)"""
    keys = sorted(messages)
    ids = b"".join(k.encode() + b"\0" for k in keys)
    strs = b"".join(messages[k].encode() + b"\0" for k in keys)
    header = 7 * 4
    table = header + len(keys) * 16
    offsets, pos = [], 0
    for k in keys:
        offsets.append((len(k.encode()), table + pos))
        pos += len(k.encode()) + 1
    trans, pos = [], 0
    for k in keys:
        trans.append((len(messages[k].encode()), table + len(ids) + pos))
        pos += len(messages[k].encode()) + 1
    data = struct.pack("<7I", 0x950412DE, 0, len(keys), header, header + len(keys) * 8, 0, 0)
    data += b"".join(struct.pack("<2I", *o) for o in offsets)
    data += b"".join(struct.pack("<2I", *t) for t in trans)
    path.parent.mkdir(parents=True)
    path.write_bytes(data + ids + strs)


def test_command_names_as_the_game_shows_them(tmp_path):
    write_mo(tmp_path / "l10n" / "en" / "LC_MESSAGES" / "input.mo", {"Trim: Nose Up": "Trim Hat - NOSE UP"})
    translate = command_translator(tmp_path, "EN")
    assert translate("Trim: Nose Up") == "Trim Hat - NOSE UP"
    assert translate("Gun Trigger") == "Gun Trigger"


def test_no_translation_file_keeps_the_names(tmp_path):
    assert command_translator(tmp_path, "fr")("Trim: Nose Up") == "Trim: Nose Up"


def test_folders_from_the_settings_are_checked(tmp_path):
    dirs = resolve_dirs(str(tmp_path), str(tmp_path), language_override="FR")
    assert dirs["language"] == "fr"
    assert [p.split(": ")[0] for p in dirs["problems"]] == [
        f"no bin/luae.exe in {tmp_path}",
        f"no Config/Input in {tmp_path}",
    ]
    ok = resolve_dirs(str(INSTALL), str(SAVED_GAMES), own_interpreter=True)
    assert ok["problems"] == []
    assert not ok["install_detected"]
