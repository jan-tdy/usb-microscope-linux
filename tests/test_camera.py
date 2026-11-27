import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from microscope.camera import apply_rotation  # noqa: E402


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
