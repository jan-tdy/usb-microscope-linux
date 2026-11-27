import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from microscope.coords import frame_to_pixmap, widget_to_frame  # noqa: E402


def test_widget_to_frame_maps_centered_pixmap():
    # A 200x150 pixmap centered in a 300x150 widget (50px empty margin each
    # side), showing a 640x480 frame: a click at the pixmap's top-left corner
    # (50, 0) in widget coordinates should land exactly at frame (0, 0).
    point = widget_to_frame(50, 0, 300, 150, 200, 150, 640, 480)
    assert point == (0.0, 0.0)


def test_widget_to_frame_scales_correctly():
    # Same layout as above; the pixmap's exact center (50+100, 0+75) should
    # map to the frame's exact center too.
    point = widget_to_frame(150, 75, 300, 150, 200, 150, 640, 480)
    assert point == (320.0, 240.0)


def test_widget_to_frame_rejects_clicks_in_the_letterbox_margin():
    # x=20 falls in the empty margin left of the 200-wide pixmap (offset 50).
    assert widget_to_frame(20, 75, 300, 150, 200, 150, 640, 480) is None


def test_widget_to_frame_handles_degenerate_sizes():
    assert widget_to_frame(10, 10, 100, 100, 0, 0, 640, 480) is None
    assert widget_to_frame(10, 10, 100, 100, 200, 150, 0, 0) is None


def test_frame_to_pixmap_is_the_inverse_scale():
    point = frame_to_pixmap(320, 240, 200, 150, 640, 480)
    assert point == (100.0, 75.0)


def test_frame_to_pixmap_handles_degenerate_frame_size():
    assert frame_to_pixmap(10, 10, 200, 150, 0, 480) is None


def test_round_trip_widget_to_frame_to_pixmap():
    frame_point = widget_to_frame(150, 75, 300, 150, 200, 150, 640, 480)
    pixmap_point = frame_to_pixmap(frame_point[0], frame_point[1], 200, 150, 640, 480)
    assert pixmap_point == (100.0, 75.0)
