import base64

import pytest

from hotas_kneeboard.kneeboard import PNG_SIGNATURE, KneeboardError, write_pages

PNG = base64.b64encode(PNG_SIGNATURE + b"rest").decode()


def test_pages_replace_ours_and_keep_the_users(tmp_path):
    folder = tmp_path / "Kneeboard" / "A-10C_2"
    folder.mkdir(parents=True)
    (folder / "HOTAS - 01 Old device.png").write_bytes(b"old")
    (folder / "my checklist.png").write_bytes(b"mine")

    result = write_pages(
        tmp_path, "A-10C_2", [{"title": "Throttle: Warthog", "png": PNG}, {"title": "Stick", "png": PNG}]
    )

    assert result["written"] == ["HOTAS - 01 Throttle_ Warthog.png", "HOTAS - 02 Stick.png"]
    assert result["removed"] == ["HOTAS - 01 Old device.png"]
    assert sorted(p.name for p in folder.iterdir()) == [
        "HOTAS - 01 Throttle_ Warthog.png",
        "HOTAS - 02 Stick.png",
        "my checklist.png",
    ]
    assert (folder / "HOTAS - 02 Stick.png").read_bytes().startswith(PNG_SIGNATURE)


@pytest.mark.parametrize("unit_type", ["../evil", "a/b", "..", "C:"])
def test_unit_type_is_a_folder_name(tmp_path, unit_type):
    with pytest.raises(KneeboardError):
        write_pages(tmp_path, unit_type, [{"title": "x", "png": PNG}])


def test_only_png_is_written(tmp_path):
    with pytest.raises(KneeboardError, match="not a PNG"):
        write_pages(tmp_path, "F-16C_50", [{"title": "x", "png": base64.b64encode(b"GIF89a").decode()}])
    with pytest.raises(KneeboardError, match="base64"):
        write_pages(tmp_path, "F-16C_50", [{"title": "x", "png": "%%%"}])
    assert not (tmp_path / "Kneeboard").exists()
