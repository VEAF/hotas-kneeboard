import base64

import pytest

from hotas_kneeboard.kneeboard import PNG_SIGNATURE, KneeboardError, is_page_of, write_pages

PNG = base64.b64encode(PNG_SIGNATURE + b"rest").decode()


def test_pages_replace_those_of_the_profile_only(tmp_path):
    folder = tmp_path / "Kneeboard" / "AH-64D_BLK_II"
    folder.mkdir(parents=True)
    keep = [
        "my checklist.png",
        "HOTAS - Warthog.png",  # the user's own, named like ours
        "HOTAS - AH-64D_BLK_II_AI_Menu - 01 Stick.png",  # another seat of the same aircraft
    ]
    for name in keep:
        (folder / name).write_bytes(b"mine")
    (folder / "HOTAS - AH-64D_BLK_II_PLT - 01 Old device.png").write_bytes(b"old")

    result = write_pages(
        tmp_path,
        "AH-64D_BLK_II",
        "AH-64D_BLK_II_PLT",
        [{"title": "Throttle: Warthog", "png": PNG}, {"title": "Stick", "png": PNG}],
    )

    written = [
        "HOTAS - AH-64D_BLK_II_PLT - 01 Throttle_ Warthog.png",
        "HOTAS - AH-64D_BLK_II_PLT - 02 Stick.png",
    ]
    assert result["written"] == written
    assert result["removed"] == ["HOTAS - AH-64D_BLK_II_PLT - 01 Old device.png"]
    assert sorted(p.name for p in folder.iterdir()) == sorted(keep + written)
    assert (folder / written[1]).read_bytes().startswith(PNG_SIGNATURE)


def test_page_names_are_recognised_exactly():
    assert is_page_of("HOTAS - A-10C II - 03 Throttle.png", "A-10C II")
    assert not is_page_of("HOTAS - A-10C II - Throttle.png", "A-10C II")
    assert not is_page_of("HOTAS - A-10C II - 03 Throttle.png.bak", "A-10C II")
    assert not is_page_of("HOTAS - A-10C - 03 Throttle.png", "A-10C II")


@pytest.mark.parametrize("unit_type", ["../evil", "a/b", "..", "C:", " . "])
def test_unit_type_is_a_folder_name(tmp_path, unit_type):
    with pytest.raises(KneeboardError):
        write_pages(tmp_path, unit_type, "p", [{"title": "x", "png": PNG}])


def test_only_png_is_written(tmp_path):
    with pytest.raises(KneeboardError, match="not a PNG"):
        write_pages(tmp_path, "F-16C_50", "p", [{"title": "x", "png": base64.b64encode(b"GIF89a").decode()}])
    with pytest.raises(KneeboardError, match="base64"):
        write_pages(tmp_path, "F-16C_50", "p", [{"title": "x", "png": "%%%"}])
    assert not (tmp_path / "Kneeboard").exists()


def test_a_failed_write_keeps_the_previous_pages(tmp_path, monkeypatch):
    folder = tmp_path / "Kneeboard" / "F-16C_50"
    folder.mkdir(parents=True)
    old = folder / "HOTAS - F-16C_50 - 01 Stick.png"
    old.write_bytes(b"old")
    calls = []

    def failing_write(self, data):
        calls.append(self)
        if len(calls) == 2:
            raise OSError("disk full")
        return len(data)

    monkeypatch.setattr("pathlib.Path.write_bytes", failing_write)
    with pytest.raises(OSError):
        write_pages(
            tmp_path, "F-16C_50", "F-16C_50", [{"title": "a", "png": PNG}, {"title": "b", "png": PNG}]
        )
    monkeypatch.undo()
    assert old.read_bytes() == b"old"
    assert [p.name for p in folder.iterdir()] == [old.name]
