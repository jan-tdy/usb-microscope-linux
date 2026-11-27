import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from microscope.camera import apply_rotation, can_capture  # noqa: E402


def _square_pattern():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[10:30, 10:30] = (255, 255, 255)  # a bright square near the top-left
    return frame


def test_zero_degrees_is_a_no_op():
    frame = _square_pattern()
    assert apply_rotation(frame, 0) is frame


def test_full_turn_is_a_no_op():
    frame = _square_pattern()
    assert apply_rotation(frame, 360) is frame


def test_180_degrees_moves_content_to_opposite_corner():
    frame = _square_pattern()
    rotated = apply_rotation(frame, 180)
    # The bright square started near the top-left; after a half turn around
    # the frame center it should land near the bottom-right instead.
    assert rotated[10:30, 10:30].mean() < 50
    assert rotated[70:90, 70:90].mean() > 200


def test_output_shape_matches_input():
    frame = _square_pattern()
    rotated = apply_rotation(frame, 37)
    assert rotated.shape == frame.shape


def _rectangular_pattern():
    frame = np.zeros((100, 200, 3), dtype=np.uint8)  # height=100, width=200
    frame[40:60, 20:40] = (255, 255, 255)
    return frame


def test_90_degrees_swaps_dimensions_without_cropping_content():
    frame = _rectangular_pattern()
    bright_pixels = int((frame > 0).sum())

    rotated = apply_rotation(frame, 90)

    assert rotated.shape == (200, 100, 3)
    assert int((rotated > 0).sum()) == bright_pixels


def test_270_degrees_swaps_dimensions_without_cropping_content():
    frame = _rectangular_pattern()
    bright_pixels = int((frame > 0).sum())

    rotated = apply_rotation(frame, 270)

    assert rotated.shape == (200, 100, 3)
    assert int((rotated > 0).sum()) == bright_pixels


def test_630_degrees_normalizes_to_270():
    frame = _rectangular_pattern()
    assert np.array_equal(apply_rotation(frame, 630), apply_rotation(frame, 270))


def test_can_capture_returns_false_for_nonexistent_device():
    # Exercises the real subprocess path end-to-end (no mocking): a device
    # that plain doesn't exist must fail, and fail promptly rather than
    # waiting out the full timeout.
    assert can_capture("/dev/this_path_should_not_exist_xyz", timeout=5.0) is False


def test_can_capture_does_not_hang_when_the_probe_times_out():
    # Regression test: a real capture node that opens but never actually
    # delivers a frame made OpenCV's own V4L2 backend block in read() for
    # a long time (~10s per attempt observed in practice) instead of
    # failing fast. The subprocess-based probe must come back as soon as
    # its timeout elapses, not hang for however long the probe itself would
    # have taken.
    with patch(
        "microscope.camera.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="probe", timeout=1.0),
    ):
        assert can_capture("/dev/video0", timeout=1.0) is False


def test_can_capture_returns_true_when_the_probe_succeeds():
    class FakeCompletedProcess:
        returncode = 0

    with patch("microscope.camera.subprocess.run", return_value=FakeCompletedProcess()):
        assert can_capture("/dev/video0") is True
