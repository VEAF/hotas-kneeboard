"""Converts the Joystick Diagrams templates (draw.io SVG) into HOTAS Kneeboard templates.

A Joystick Diagrams template is a draw.io drawing exported to SVG: the device picture, leader
lines, notes, and one text box per input holding a token (``Button_14``, ``POV_1_U``,
``AXIS_X``) that Joystick Diagrams replaces with the command. For each template this script
writes ``<library>/<id>/``:

- ``background.svg``: the drawing without the token boxes (leader lines, notes and credits stay,
  so the label boxes land where the lines point); draw.io's HTML labels become plain SVG text,
  which the browser can draw into a PNG and a PDF;
- ``template.json``: the box of each token (``more_boxes`` when it is drawn more than once), keyed by DCS input name (``JOY_BTN14``,
  ``JOY_BTN_POV1_U``, ``JOY_X``), plus the DCS device names and the credits from
  ``jd_templates.json``.

Usage: python scripts/convert_jd_templates.py <joystick-diagrams>/templates [library folder]
Prints, per template, what it found and the token-like texts it did not recognise.
"""

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
XHTML = "http://www.w3.org/1999/xhtml"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)

HERE = Path(__file__).resolve().parent
METADATA = HERE / "jd_templates.json"
DEFAULT_LIBRARY = HERE.parent / "hotas_kneeboard" / "library"
SOURCE_URL = "https://github.com/Rexeh/joystick-diagrams/blob/master/templates/"

AXES = {"X", "Y", "Z", "RX", "RY", "RZ"}
HAT_DIRECTIONS = {"U", "UR", "R", "DR", "D", "DL", "L", "UL"}
# texts Joystick Diagrams fills in itself: nothing to keep once converted
PLACEHOLDERS = {"TEMPLATE_NAME", "JOYSTICK NAME"}
# looks like a token, to report the ones dcs_input does not know
TOKEN_LIKE = re.compile(r"^(button|btn|pov|hat|axis|slider)_\w+$|^\w+_axis$", re.IGNORECASE)
# draw.io's fallback for viewers without foreignObject, useless once the labels are SVG text
DRAWIO_FALLBACKS = ("Text is not SVG - cannot display", "Viewer does not support full SVG 1.1")


def tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def dcs_input(token: str) -> str | None:
    """DCS input name of a Joystick Diagrams token, or None when it is not one."""
    t = token.strip().upper().replace(" ", "_")
    if m := re.fullmatch(r"BUTTON_?(\d+)", t):
        return f"JOY_BTN{int(m[1])}"
    # POV_1_U; POV_L and BUTTON_POV_R (hat 1) in a few templates
    if (m := re.fullmatch(r"(?:BUTTON_)?POV_?(\d*)_([UDLR]{1,2})", t)) and m[2] in HAT_DIRECTIONS:
        return f"JOY_BTN_POV{int(m[1] or 1)}_{m[2]}"
    m = re.fullmatch(r"AXIS_(\w+)", t) or re.fullmatch(r"(\w+)_AXIS", t)
    axis = m[1] if m else None
    if axis in AXES:
        return f"JOY_{axis}"
    slider = re.fullmatch(r"(?:AXIS_)?SLIDER_?(\d*)", t)
    if slider:
        return f"JOY_SLIDER{int(slider[1] or 1) or 1}"
    return None


def style_of(element: ET.Element) -> dict[str, str]:
    style = {}
    for part in (element.get("style") or "").split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            style[key.strip()] = value.strip()
    return style


def px(value: str | None, default: float = 0.0) -> float:
    m = re.match(r"-?[\d.]+", value or "")
    return float(m[0]) if m else default


def html_lines(element: ET.Element) -> list[str]:
    """Text lines of draw.io's HTML label: <br> and block <div> break lines."""
    lines, current = [], []

    def flush():
        text = re.sub(r"\s+", " ", "".join(current)).strip()
        if text:
            lines.append(text)
        current.clear()

    def walk(node: ET.Element, top: bool):
        name = tag(node)
        if name == "br":
            flush()
        elif name == "div" and not top and current:
            flush()
        if node.text:
            current.append(node.text)
        for child in node:
            walk(child, False)
            if child.tail:
                current.append(child.tail)
        if name == "div" and not top:
            flush()

    walk(element, True)
    flush()
    return [html.unescape(line) for line in lines]


class Label:
    """A draw.io label: ``<g><switch><foreignObject>…html…</foreignObject><text>…</text></switch></g>``"""

    def __init__(self, group: ET.Element):
        self.group = group
        self.switch = group.find(f"{{{SVG}}}switch")
        self.foreign = self.switch.find(f"{{{SVG}}}foreignObject") if self.switch is not None else None
        texts = list(group.iter(f"{{{SVG}}}text"))
        self.fallback = texts[0] if texts else None
        self.lines = html_lines(self.foreign) if self.foreign is not None else []
        if not self.lines and self.fallback is not None:
            self.lines = [(self.fallback.text or "").strip()]
        self.text = " ".join(self.lines)

    def box(self) -> tuple[float, float, float, float] | None:
        """Where draw.io laid the label out: its outer div (width, padding-top, margin-left)."""
        if self.foreign is None:
            return None
        outer = self.foreign.find(f"{{{XHTML}}}div")
        if outer is None:
            return None
        style = style_of(outer)
        width, top, left = px(style.get("width")), px(style.get("padding-top")), px(style.get("margin-left"))
        inner_font = max(
            (px(style_of(d).get("font-size"), 0) for d in outer.iter(f"{{{XHTML}}}div")), default=0
        )
        height = max(inner_font or 12, 12) * 1.2 * max(len(self.lines), 1) + 4
        if "center" in style.get("align-items", "center"):
            return (left - 1, top - height / 2, width + 2, height)
        return (left - 1, top, width + 2, height)

    def center(self) -> tuple[float, float] | None:
        box = self.box()
        if box:
            return (box[0] + box[2] / 2, box[1] + box[3] / 2)
        if self.fallback is not None:
            return (px(self.fallback.get("x")), px(self.fallback.get("y")))
        return None

    def to_svg_text(self) -> ET.Element | None:
        """Plain SVG text with the label's lines, where draw.io's fallback <text> stands."""
        fallback = self.fallback
        if fallback is None or not self.lines or self.text in DRAWIO_FALLBACKS:
            return None
        text = ET.Element(f"{{{SVG}}}text", dict(fallback.attrib))
        size = px(fallback.get("font-size"), 12)
        line_height = size * 1.2
        x, y = fallback.get("x", "0"), px(fallback.get("y"))
        first = y - (len(self.lines) - 1) * line_height / 2
        if len(self.lines) == 1:
            text.text = self.lines[0]
        else:
            for i, line in enumerate(self.lines):
                span = ET.SubElement(text, f"{{{SVG}}}tspan", {"x": x, "y": f"{first + i * line_height:.2f}"})
                span.text = line
        return text


def is_label_group(element: ET.Element) -> bool:
    return tag(element) == "g" and any(tag(c) == "switch" for c in element)


def drawables(root: ET.Element) -> list[ET.Element]:
    """Shapes and labels in drawing order (the label <g> as one item)."""
    out = []

    def walk(node):
        for child in node:
            if is_label_group(child):
                out.append(child)
            elif tag(child) == "g" or tag(child) == "a":
                walk(child)
            elif tag(child) in ("rect", "path", "ellipse", "image", "text", "polygon", "polyline", "line"):
                out.append(child)

    walk(root)
    return out


def inside(point, rect, margin=2.0) -> bool:
    x, y = point
    rx, ry, rw, rh = rect
    return rx - margin <= x <= rx + rw + margin and ry - margin <= y <= ry + rh + margin


def rect_box(element: ET.Element) -> tuple[float, float, float, float]:
    return tuple(px(element.get(k)) for k in ("x", "y", "width", "height"))


class Tokens:
    """The token boxes of a drawing: where each input's label goes, and what to remove."""

    def __init__(self, root: ET.Element, remap: dict[str, str]):
        self.inputs: dict[str, dict] = {}
        self.unknown: list[str] = []
        self.duplicates: list[str] = []
        self.remove: list[ET.Element] = []
        items = drawables(root)
        for index, element in enumerate(items):
            if is_label_group(element):
                self._label(Label(element), items[index - 1] if index else None, remap)

    def _label(self, label: Label, previous: ET.Element | None, remap: dict[str, str]) -> None:
        key = dcs_input(label.text)
        if not key and label.text not in PLACEHOLDERS:
            if label.text in DRAWIO_FALLBACKS:
                self.remove.append(label.group)
            elif TOKEN_LIKE.match(label.text):
                self.unknown.append(label.text)
            return
        self.remove.append(label.group)
        # the box drawn under the token, else where draw.io laid the text out
        center, box = label.center(), None
        if previous is not None and tag(previous) == "rect" and center and inside(center, rect_box(previous)):
            box = rect_box(previous)
            self.remove.append(previous)
        box = box or label.box()
        if key is None:  # a placeholder
            return
        if box is None:
            self.unknown.append(f"{label.text} (no box)")
            return
        key = remap.get(key, key)
        box = [round(v, 1) for v in box]
        if key in self.inputs:
            # the same input drawn twice (two views of a device): the label goes in both
            self.inputs[key].setdefault("more_boxes", []).append(box)
            self.duplicates.append(key)
        else:
            self.inputs[key] = {"box": box}


def clean_drawing(root: ET.Element, remove: list[ET.Element]) -> None:
    """Removes the token boxes, draw.io's notices and the groups left empty; turns the remaining
    HTML labels into plain SVG text."""
    parents = {child: parent for parent in root.iter() for child in parent}
    root.attrib.pop("content", None)  # the compressed draw.io model: not ours to keep
    for element in remove:
        parent = parents.get(element)
        if parent is not None and element in list(parent):
            parent.remove(element)
    # draw.io's notice for viewers without foreignObject (a link in a <switch> at the end), and the
    # groups emptied above
    for element in list(root.iter()):
        for child in list(element):
            text = "".join(child.itertext()).strip()
            if tag(child) in ("a", "switch") and text in DRAWIO_FALLBACKS:
                element.remove(child)
            elif tag(child) in ("g", "a") and not list(child) and not text:
                element.remove(child)
    for group in [g for g in root.iter() if is_label_group(g)]:
        label = Label(group)
        replacement = label.to_svg_text()
        group.remove(label.switch)
        if replacement is not None:
            group.append(replacement)


def drawing_size(root: ET.Element) -> list[float]:
    view_box = (root.get("viewBox") or "").split()
    if len(view_box) == 4:
        return [float(view_box[2]), float(view_box[3])]
    return [px(root.get("width")), px(root.get("height"))]


def convert(source: Path, out_dir: Path, meta: dict) -> dict:
    tree = ET.parse(source)
    root = tree.getroot()
    tokens = Tokens(root, meta.get("remap", {}))
    clean_drawing(root, tokens.remove)

    folder = out_dir / meta["id"]
    folder.mkdir(parents=True, exist_ok=True)
    tree.write(folder / "background.svg", encoding="utf-8", xml_declaration=True)
    data = {
        "format": 1,
        "name": meta.get("name") or source.stem,
        "devices": meta.get("devices", []),
        "image": "background.svg",
        "size": drawing_size(root),
        "inputs": dict(sorted(tokens.inputs.items(), key=lambda kv: input_order(kv[0]))),
        "credits": {
            "author": meta.get("author", "Joystick Diagrams contributors"),
            "source": SOURCE_URL + meta["source"].replace(" ", "%20"),
            "license": "GPL-2.0",
            "converted_by": "scripts/convert_jd_templates.py",
        },
        # numbering checked on the real device (lot L3), else null: Joystick Diagrams' as drawn
        "checked": meta.get("checked"),
    }
    (folder / "template.json").write_text(
        json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return {
        "id": meta["id"],
        "inputs": len(tokens.inputs),
        "unknown": tokens.unknown,
        "duplicates": tokens.duplicates,
    }


def input_order(key: str) -> str:
    return re.sub(r"\d+", lambda m: f"{int(m[0]):04d}", key)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    templates_dir = Path(sys.argv[1])
    library = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_LIBRARY
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))["templates"]
    sources = sorted(p.relative_to(templates_dir).as_posix() for p in templates_dir.rglob("*.svg"))
    missing = [s for s in sources if s not in metadata]
    if missing:
        print("no entry in jd_templates.json for:\n  " + "\n  ".join(missing))
        return 1
    status = 0
    for relative in sources:
        meta = metadata[relative] | {"source": relative}
        if meta.get("skip"):
            print(f"-- {relative}: skipped ({meta['skip']})")
            continue
        report = convert(templates_dir / relative, library, meta)
        notes = []
        if report["unknown"]:
            notes.append(f"not recognised: {', '.join(report['unknown'])}")
        if report["duplicates"]:
            notes.append(f"drawn more than once: {', '.join(sorted(set(report['duplicates'])))}")
        print(f"{report['id']}: {report['inputs']} inputs" + (f" ; {' ; '.join(notes)}" if notes else ""))
        if report["inputs"] == 0:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
