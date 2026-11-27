import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from microscope.v4l2_controls import _parse_list_ctrls  # noqa: E402

SAMPLE_OUTPUT = """\
                     brightness 0x00980900 (int)    : min=0 max=255 step=1 default=128 value=128
white_balance_automatic 0x0098090c (bool)   : default=1 value=1
           power_line_frequency 0x00980918 (menu)   : min=0 max=2 default=1 value=1
         backlight_compensation 0x0098091c (int)    : min=0 max=2 step=1 default=1 value=1
                  exposure_auto (menu)   : min=0 max=3 default=3 value=3
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
    assert "exposure_auto" not in names


def test_finds_zoom_and_led_controls():
    controls = _parse_list_ctrls(SAMPLE_OUTPUT)
    names = [c["name"] for c in controls]
    assert "zoom_absolute" in names
    assert "led1_mode" in names


def test_empty_output_returns_no_controls():
    assert _parse_list_ctrls("") == []
