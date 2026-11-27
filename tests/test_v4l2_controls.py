import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from microscope.v4l2_controls import (  # noqa: E402
    _parse_get_ctrl,
    _parse_list_ctrls,
    _parse_list_devices,
)

LIST_DEVICES_OUTPUT = """\
UGREEN Camera: UGREEN Camera (usb-0000:00:14.0-2.3):
\t/dev/video0
\t/dev/video1
\t/dev/media0

USB2.0 UVC PC Camera: USB2.0 UV (usb-0000:00:14.0-7):
\t/dev/video2
\t/dev/video3
\t/dev/media1

"""

SAMPLE_OUTPUT = """\
                     brightness 0x00980900 (int)    : min=0 max=255 step=1 default=128 value=128
white_balance_automatic 0x0098090c (bool)   : default=1 value=1
           power_line_frequency 0x00980918 (menu)   : min=0 max=2 default=1 value=1
\t\t0: Disabled
\t\t1: 50 Hz
\t\t2: 60 Hz
                  exposure_auto 0x009a0901 (menu)   : min=0 max=3 default=0 value=3
\t\t1: Manual Mode
\t\t3: Aperture Priority Mode
         backlight_compensation 0x0098091c (int)    : min=0 max=2 step=1 default=1 value=1
                      focus_auto (menu)   : min=0 max=3 default=3 value=3
                   zoom_absolute 0x009a090d (int)    : min=0 max=317 step=1 default=0 value=100
                       led1_mode 0x0a046d05 (int)    : min=0 max=3 step=1 default=0 value=0
"""


def test_parses_int_control_with_range_and_value():
    controls = _parse_list_ctrls(SAMPLE_OUTPUT)
    brightness = next(c for c in controls if c["name"] == "brightness")
    assert brightness["type"] == "int"
    assert brightness["min"] == 0
    assert brightness["max"] == 255
    assert brightness["value"] == 128


def test_parses_bool_control():
    controls = _parse_list_ctrls(SAMPLE_OUTPUT)
    wb_auto = next(c for c in controls if c["name"] == "white_balance_automatic")
    assert wb_auto["type"] == "bool"
    assert wb_auto["value"] == 1


def test_skips_line_missing_control_id():
    controls = _parse_list_ctrls(SAMPLE_OUTPUT)
    names = [c["name"] for c in controls]
    assert "focus_auto" not in names


def test_parses_menu_items_under_a_menu_control():
    controls = _parse_list_ctrls(SAMPLE_OUTPUT)
    exposure_auto = next(c for c in controls if c["name"] == "exposure_auto")
    assert exposure_auto["type"] == "menu"
    assert exposure_auto["menu_items"] == {1: "Manual Mode", 3: "Aperture Priority Mode"}


def test_non_menu_controls_have_no_menu_items():
    controls = _parse_list_ctrls(SAMPLE_OUTPUT)
    brightness = next(c for c in controls if c["name"] == "brightness")
    assert brightness["menu_items"] == {}


def test_parse_get_ctrl_extracts_value():
    assert _parse_get_ctrl("brightness: 128\n") == 128


def test_parse_get_ctrl_returns_none_on_unparsable_output():
    assert _parse_get_ctrl("") is None


def test_finds_zoom_and_led_controls():
    controls = _parse_list_ctrls(SAMPLE_OUTPUT)
    names = [c["name"] for c in controls]
    assert "zoom_absolute" in names
    assert "led1_mode" in names


def test_empty_output_returns_no_controls():
    assert _parse_list_ctrls("") == []


def test_parses_list_devices_groups_nodes_by_camera():
    mapping = _parse_list_devices(LIST_DEVICES_OUTPUT)
    assert mapping["/dev/video0"] == "UGREEN Camera"
    assert mapping["/dev/video1"] == "UGREEN Camera"
    assert mapping["/dev/video2"] == "USB2.0 UVC PC Camera"
    assert mapping["/dev/video3"] == "USB2.0 UVC PC Camera"
    assert "/dev/media0" not in mapping
    assert "/dev/media1" not in mapping
