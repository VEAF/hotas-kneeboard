from hotas_kneeboard.pages import build_page, pair_label, split_device_name


def binding(key, command, reformers=()):
    return {"key": key, "command": command, "reformers": list(reformers)}


def page(*bindings, name="Throttle - HOTAS Warthog {8F576560-6142-11ef-8006-444553540000}"):
    return build_page({"name": name, "source": "effective", "bindings": list(bindings)})


def test_device_name_without_guid():
    assert split_device_name("Throttle - HOTAS Warthog {8F576560-6142-11ef-8006-444553540000}") == (
        "Throttle - HOTAS Warthog",
        "{8F576560-6142-11ef-8006-444553540000}",
    )
    assert split_device_name("No Guid") == ("No Guid", "")


def test_released_position_goes_on_its_button():
    p = page(binding("JOY_BTN17", "Landing Gear Up"), binding("JOY_BTN17_OFF", "Landing Gear Down"))
    assert list(p.inputs) == ["JOY_BTN17"]
    label = p.inputs["JOY_BTN17"][""]
    assert (label.pressed, label.released) == (["Landing Gear Up"], ["Landing Gear Down"])
    assert label.text == "Landing Gear Up / Down"


def test_released_alone_keeps_its_command():
    label = page(binding("JOY_BTN9_OFF", "Switch Released")).inputs["JOY_BTN9"][""]
    assert (label.pressed, label.released, label.text) == ([], ["Switch Released"], "Switch Released")


def test_pair_keeps_whole_words_and_never_empties_the_released_side():
    assert pair_label("LG Handle - UP", "LG Handle - DN") == "LG Handle - UP / DN"
    assert pair_label("Master switch SAFE", "Master switch ARM") == "Master switch SAFE / ARM"
    assert pair_label("Gear", "Gear") == "Gear / Gear"
    assert pair_label("APU ON", "Flaps Down") == "APU ON / Flaps Down"
    # several commands on one side: no shortening, it would mix them up
    assert pair_label("A on / B on", "A off") == "A on / B on / A off"


def test_layers_are_separate_and_base_comes_first():
    p = page(
        binding("JOY_BTN2", "IFF OUT", ["Paddle"]),
        binding("JOY_BTN2", "IFF IN"),
        binding("JOY_BTN4", "Radio", ["JOY_BTN5", "Paddle"]),
    )
    assert p.inputs["JOY_BTN2"][""].text == "IFF IN"
    assert p.inputs["JOY_BTN2"]["Paddle"].text == "IFF OUT"
    assert p.layers == ["", "JOY_BTN5 + Paddle", "Paddle"]


def test_commands_sharing_an_input_are_all_kept():
    label = page(binding("JOY_BTN6", "Gun Trigger"), binding("JOY_BTN6", "Sensor Select")).inputs["JOY_BTN6"][
        ""
    ]
    assert label.text == "Gun Trigger / Sensor Select"


def test_inputs_in_natural_order_and_keyboard_keys_dropped():
    p = page(
        binding("JOY_BTN10", "b"), binding("JOY_BTN2", "a"), binding("LCtrl", "kbd"), binding("JOY_X", "x")
    )
    assert list(p.inputs) == ["JOY_BTN2", "JOY_BTN10", "JOY_X"]
    assert p.binding_count == 3


def test_as_dict():
    d = page(binding("JOY_BTN1", "Fire")).as_dict()
    assert d["name"] == "Throttle - HOTAS Warthog"
    assert d["inputs"] == {"JOY_BTN1": {"": {"text": "Fire", "pressed": ["Fire"], "released": []}}}
