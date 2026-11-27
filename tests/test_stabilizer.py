import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from microscope.stabilizer import VibrationStabilizer  # noqa: E402


def _make_pattern():
    frame = np.zeros((240, 320), dtype=np.uint8)
    for y in range(30, 210, 45):
        for x in range(30, 300, 45):
            frame[y:y + 10, x:x + 10] = 255
    return frame


def test_estimate_motion_detects_known_translation():
    base = _make_pattern()
    dx_true, dy_true = 8.0, -5.0
    shift_matrix = np.array([[1, 0, dx_true], [0, 1, dy_true]], dtype=np.float32)
    shifted = cv2.warpAffine(base, shift_matrix, (base.shape[1], base.shape[0]))

    dx, dy, da = VibrationStabilizer._estimate_motion(base, shifted)

    assert abs(dx - dx_true) < 1.5
    assert abs(dy - dy_true) < 1.5
    assert abs(da) < 0.05


def test_estimate_motion_returns_zero_on_blank_frames():
    blank = np.zeros((120, 160), dtype=np.uint8)
    assert VibrationStabilizer._estimate_motion(blank, blank) == (0.0, 0.0, 0.0)


def test_stabilize_returns_original_on_first_frame():
    stabilizer = VibrationStabilizer()
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frame[40:80, 40:80] = (255, 255, 255)

    result = stabilizer.stabilize(frame)

    assert np.array_equal(result, frame)


def test_reset_clears_internal_state():
    stabilizer = VibrationStabilizer()
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    stabilizer.stabilize(frame)
    stabilizer.stabilize(frame)

    stabilizer.reset()

    assert stabilizer._prev_gray is None
    assert len(stabilizer._history) == 0
    assert np.array_equal(stabilizer._trajectory, np.zeros(3))


def test_stabilize_reduces_jitter_amplitude():
    # Regression test: an earlier version added this frame's own raw motion
    # back on top of the trajectory correction, which *amplified* jitter
    # instead of cancelling it. Feed a static scene with pure back-and-forth
    # jitter (no net drift) through the stabilizer and check the residual
    # frame-to-frame motion of the output is clearly smaller than the input's.
    base = cv2.cvtColor(_make_pattern(), cv2.COLOR_GRAY2BGR)
    rng = np.random.default_rng(0)
    jitter = rng.normal(0, 4.0, size=40)
    jitter -= jitter.mean()

    frames = []
    for shift in jitter:
        matrix = np.array([[1, 0, shift], [0, 1, 0]], dtype=np.float32)
        frames.append(cv2.warpAffine(base, matrix, (base.shape[1], base.shape[0])))

    stabilizer = VibrationStabilizer()
    outputs = [stabilizer.stabilize(f) for f in frames]

    def residual_std(sequence):
        grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in sequence]
        deltas = [
            VibrationStabilizer._estimate_motion(a, b)[0] for a, b in zip(grays[:-1], grays[1:])
        ]
        return float(np.std(deltas))

    assert residual_std(outputs) < residual_std(frames) * 0.5


def test_stabilize_output_matches_input_shape():
    stabilizer = VibrationStabilizer()
    base = _make_pattern()
    frame = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
    stabilizer.stabilize(frame)

    shifted = np.roll(frame, shift=3, axis=1)
    result = stabilizer.stabilize(shifted)

    assert result.shape == frame.shape
