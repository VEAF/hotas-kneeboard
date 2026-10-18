import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "convert_jd_templates.py"
spec = importlib.util.spec_from_file_location("convert_jd_templates", SCRIPT)
converter = importlib.util.module_from_spec(spec)
sys.modules["convert_jd_templates"] = converter
spec.loader.exec_module(converter)

SAMPLES = Path(__file__).parent / "jd_samples"
META = {"id": "t", "devices": ["Dev"], "source": "Dir/T.svg"}


def label(text, x, y, width=80):
    return (
        '<g transform="translate(-0.5 -0.5)"><switch><foreignObject width="100%" height="100%">'
        f'<div xmlns="http://www.w3.org/1999/xhtml" style="display: flex; align-items: unsafe center; '
        f'justify-content: unsafe center; width: {width - 2}px; height: 1px; padding-top: {y}px; margin-left: {x + 1}px;">'
        f'<div style="font-size: 0px;"><div style="display: inline-block; font-size: 10px;">{text}</div></div></div>'
        f'</foreignObject><text x="{x + width / 2}" y="{y + 3}" font-size="10px" text-anchor="middle">'
        f"{text.split('<')[0]}</text></switch></g>"
    )


def svg(body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="400px" height="300px" viewBox="-0.5 -0.5 400 300" content="drawio-model"><g>{body}</g></svg>'
    )


def run(tmp_path, body, meta=META):
    source = tmp_path / "in.svg"
    source.write_text(svg(body), encoding="utf-8")
    report = converter.convert(source, tmp_path / "out", meta)
    folder = tmp_path / "out" / meta["id"]
    data = json.loads((folder / "template.json").read_text(encoding="utf-8"))
    background = (folder / "background.svg").read_text(encoding="utf-8")
    return report, data, background


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("Button_14", "JOY_BTN14"),
        ("BUTTON_5", "JOY_BTN5"),
        ("POV_1_U", "JOY_BTN_POV1_U"),
        ("Pov_2_DL", "JOY_BTN_POV2_DL"),
        ("POV_L", "JOY_BTN_POV1_L"),
        ("Button_Pov_UR", "JOY_BTN_POV1_UR"),
        ("AXIS_X", "JOY_X"),
        ("Axis_RZ", "JOY_RZ"),
        ("X_AXIS", "JOY_X"),
        ("Axis_Slider", "JOY_SLIDER1"),
        ("SLIDER_2", "JOY_SLIDER2"),
        ("POV_1_LL", None),
        ("Trigger", None),
        ("AXIS", None),
    ],
)
def test_tokens(token, expected):
    assert converter.dcs_input(token) == expected


def test_flat_drawing(tmp_path):
    body = (
        '<image x="0" y="0" width="400" height="300" xlink:href="data:image/png;base64,AA"/>'
        '<rect x="10" y="20" width="80" height="20" fill="#fff" stroke="#000"/>'
        + label("Button_3", 10, 30)
        + '<path d="M 90 30 L 200 100" fill="none" stroke="#000"/>'
        + '<rect x="10" y="60" width="80" height="20"/>'
        + label("PUSH<br/>TO TALK", 10, 70)
        + label("TEMPLATE_NAME", 200, 10)
    )
    report, data, background = run(tmp_path, body)
    assert data["inputs"] == {"JOY_BTN3": {"box": [10.0, 20.0, 80.0, 20.0]}}
    assert data["size"] == [400.0, 300.0]
    assert data["devices"] == ["Dev"]
    assert data["credits"]["source"].endswith("templates/Dir/T.svg")
    assert report["unknown"] == []
    # token box and placeholder gone; picture, leader line and note kept, as plain SVG text
    assert "Button_3" not in background
    assert "TEMPLATE_NAME" not in background
    assert 'd="M 90 30 L 200 100"' in background
    assert "foreignObject" not in background
    assert "drawio-model" not in background
    assert ">PUSH</tspan>" in background
    assert ">TO TALK</tspan>" in background
    assert 'x="10" y="60"' in background  # the note's own box is not a token box


def test_nested_drawing_and_input_drawn_twice(tmp_path):
    body = (
        '<g><rect x="10" y="20" width="80" height="20"/></g>'
        f"<g>{label('POV_1_U', 10, 30)}</g>"
        '<g><rect x="200" y="20" width="80" height="20"/></g>'
        f"<g>{label('POV_1_U', 200, 30)}</g>"
        f"<g>{label('Axis_Weird', 10, 200)}</g>"
    )
    report, data, background = run(tmp_path, body)
    assert data["inputs"] == {
        "JOY_BTN_POV1_U": {"box": [10.0, 20.0, 80.0, 20.0], "more_boxes": [[200.0, 20.0, 80.0, 20.0]]}
    }
    assert report["unknown"] == ["Axis_Weird"]
    assert "<rect" not in background  # both token boxes removed, empty wrappers too
    assert "<g />" not in background


def test_remap_after_checking_the_real_numbering(tmp_path):
    body = '<rect x="10" y="20" width="80" height="20"/>' + label("POV_2_U", 10, 30)
    _, data, _ = run(tmp_path, body, META | {"remap": {"JOY_BTN_POV2_U": "JOY_BTN_POV1_U"}})
    assert list(data["inputs"]) == ["JOY_BTN_POV1_U"]


def test_real_template(tmp_path):
    source = SAMPLES / "T.16000M Joystick Right Handed.svg"
    report = converter.convert(source, tmp_path, META | {"id": "t16000m"})
    data = json.loads((tmp_path / "t16000m" / "template.json").read_text(encoding="utf-8"))
    expected = {f"JOY_BTN{n}" for n in range(1, 17)} | {
        f"JOY_BTN_POV1_{d}" for d in ("U", "UR", "R", "DR", "D", "DL", "L", "UL")
    }
    assert set(data["inputs"]) == expected
    assert report["unknown"] == []
    background = (tmp_path / "t16000m" / "background.svg").read_text(encoding="utf-8")
    for gone in ("Button_1<", "Pov_1_U", "TEMPLATE_NAME", "Text is not SVG"):
        assert gone not in background
    for kept in ("Trigger", "Created by Joystick Diagrams", "data:image/"):
        assert kept in background


def test_metadata_covers_every_template_once():
    metadata = json.loads(converter.METADATA.read_text(encoding="utf-8"))["templates"]
    ids = [m["id"] for m in metadata.values()]
    assert len(ids) == len(set(ids))
    assert len(metadata) == 46


def test_maintained_templates_are_not_converted_again(tmp_path, monkeypatch, capsys):
    source = tmp_path / "templates"
    (source / "Dir").mkdir(parents=True)
    (source / "Dir" / "T.svg").write_text(
        svg('<rect x="1" y="1" width="9" height="9"/>' + label("Button_1", 1, 5)), encoding="utf-8"
    )
    metadata = tmp_path / "jd_templates.json"
    metadata.write_text(
        json.dumps({"templates": {"Dir/T.svg": {"id": "t", "maintained": True}}}), encoding="utf-8"
    )
    monkeypatch.setattr(converter, "METADATA", metadata)
    monkeypatch.setattr(sys, "argv", ["convert", str(source), str(tmp_path / "library")])
    assert converter.main() == 0
    assert not (tmp_path / "library" / "t").exists()
    assert "maintained by hand" in capsys.readouterr().out
