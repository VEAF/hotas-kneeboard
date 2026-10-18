"""What a device page shows: per input and per modifier layer, the commands bound to it.

The engine gives one binding per (command, combo). A page groups them by input (``JOY_BTN17``) and
layer (the modifiers held, e.g. ``Paddle``; ``""`` for the base layer). A switch's released
position (``JOY_BTN17_OFF``) goes on its input, next to the pressed one: "LG Handle - UP / DN".
"""

import re
from dataclasses import dataclass, field

RELEASED_SUFFIX = "_OFF"
GUID = re.compile(r"^(?P<name>.*?)\s*(?P<guid>\{[0-9A-Fa-f-]+\})$")
_NUMBER = re.compile(r"\d+")

BASE_LAYER = ""


def split_device_name(full_name: str) -> tuple[str, str]:
    """``"Throttle - HOTAS Warthog {8F57…}"`` -> ``("Throttle - HOTAS Warthog", "{8F57…}")``"""
    match = GUID.match(full_name)
    if not match:
        return full_name, ""
    return match["name"], match["guid"]


def layer_name(reformers: list[str]) -> str:
    return " + ".join(sorted(reformers))


def input_sort_key(key: str) -> str:
    """Natural order: JOY_BTN2 before JOY_BTN10"""
    return _NUMBER.sub(lambda m: f"{int(m[0]):06d}", key)


def pair_label(pressed: str, released: str) -> str:
    """Both positions of a switch on one label, without repeating their common words:
    ("Landing Gear Up", "Landing Gear Down") -> "Landing Gear Up / Down"."""
    on, off = pressed.split(" "), released.split(" ")
    common = 0
    if " / " not in pressed and " / " not in released:
        while common < min(len(on), len(off)) - 1 and on[common] == off[common]:
            common += 1
    return f"{pressed} / {' '.join(off[common:])}"


@dataclass
class Label:
    pressed: list[str] = field(default_factory=list)
    released: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        pressed, released = " / ".join(self.pressed), " / ".join(self.released)
        if pressed and released:
            return pair_label(pressed, released)
        return pressed or released

    def as_dict(self) -> dict:
        return {"text": self.text, "pressed": self.pressed, "released": self.released}


@dataclass
class DevicePage:
    full_name: str
    source: str  # "effective" (defaults + diff) or "diff" (only what the diff adds)
    error: str | None
    inputs: dict[str, dict[str, Label]]

    @property
    def name(self) -> str:
        return split_device_name(self.full_name)[0]

    @property
    def layers(self) -> list[str]:
        found = {layer for labels in self.inputs.values() for layer in labels}
        return sorted(found, key=lambda layer: (layer != BASE_LAYER, layer))

    @property
    def binding_count(self) -> int:
        return sum(
            len(label.pressed) + len(label.released)
            for labels in self.inputs.values()
            for label in labels.values()
        )

    def as_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "name": self.name,
            "source": self.source,
            "error": self.error,
            "layers": self.layers,
            "binding_count": self.binding_count,
            "inputs": {
                key: {layer: label.as_dict() for layer, label in labels.items()}
                for key, labels in self.inputs.items()
            },
        }


def build_page(device: dict) -> DevicePage:
    """Page of one device of the engine's output."""
    inputs: dict[str, dict[str, Label]] = {}
    for binding in device.get("bindings") or []:
        key, released = binding["key"], False
        if key.endswith(RELEASED_SUFFIX):
            key, released = key.removesuffix(RELEASED_SUFFIX), True
        # keyboard keys a module's joystick profile may hold are not on the device
        if not key.startswith("JOY_"):
            continue
        layer = layer_name(binding.get("reformers") or [])
        label = inputs.setdefault(key, {}).setdefault(layer, Label())
        commands = label.released if released else label.pressed
        command = binding.get("command") or ""
        if command not in commands:
            commands.append(command)
    ordered = {key: inputs[key] for key in sorted(inputs, key=input_sort_key)}
    return DevicePage(
        full_name=device["name"],
        source=device.get("source", "effective"),
        error=device.get("error"),
        inputs=ordered,
    )
