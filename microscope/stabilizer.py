from collections import deque

import cv2
import numpy as np


class VibrationStabilizer:
    """Cancels small frame-to-frame jitter while letting a deliberate,
    larger movement of the microscope (repositioning it by hand) pass
    through untouched.

    Tracks sparse feature points frame-to-frame to estimate a rigid
    (translation + rotation) motion, keeps a short causal moving average
    of the camera's cumulative path as a stand-in for "where it meant to
    be", and warps each frame back toward that average — clamped to a
    small pixel/angle range so it only ever corrects jitter, never chases
    a real, sustained move.
    """

    def __init__(self, smoothing_window=15, max_shift=30.0, max_angle=0.05):
        self.smoothing_window = smoothing_window
        self.max_shift = max_shift
        self.max_angle = max_angle
        self._prev_gray = None
        self._trajectory = np.zeros(3, dtype=np.float64)
        self._history = deque(maxlen=smoothing_window)

    def reset(self):
        self._prev_gray = None
        self._trajectory[:] = 0.0
        self._history.clear()

    def stabilize(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._prev_gray is None:
            self._prev_gray = gray
            self._history.append(self._trajectory.copy())
            return frame

        dx, dy, da = self._estimate_motion(self._prev_gray, gray)
        self._prev_gray = gray
        self._trajectory += (dx, dy, da)
        self._history.append(self._trajectory.copy())

        smoothed = np.mean(self._history, axis=0)
        # trajectory is the raw, uncorrected cumulative drift of this frame's
        # content relative to the first frame; diff is exactly how far this
        # frame needs to be shifted to land on the smoothed path instead —
        # dx/dy/da (this frame's own incremental motion) must NOT be added
        # again on top, or the correction doubles back and amplifies the
        # jitter it was meant to cancel.
        diff = smoothed - self._trajectory
        diff[0] = float(np.clip(diff[0], -self.max_shift, self.max_shift))
        diff[1] = float(np.clip(diff[1], -self.max_shift, self.max_shift))
        diff[2] = float(np.clip(diff[2], -self.max_angle, self.max_angle))

        corrected_dx, corrected_dy, corrected_da = diff[0], diff[1], diff[2]

        cos_a, sin_a = np.cos(corrected_da), np.sin(corrected_da)
        transform = np.array(
            [[cos_a, -sin_a, corrected_dx], [sin_a, cos_a, corrected_dy]],
            dtype=np.float32,
        )
        height, width = frame.shape[:2]
        return cv2.warpAffine(frame, transform, (width, height), borderMode=cv2.BORDER_REPLICATE)

    @staticmethod
    def _estimate_motion(prev_gray, gray):
        points = cv2.goodFeaturesToTrack(prev_gray, maxCorners=200, qualityLevel=0.01, minDistance=30)
        if points is None or len(points) < 10:
            return 0.0, 0.0, 0.0

        tracked, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, points, None)
        if tracked is None:
            return 0.0, 0.0, 0.0

        status = status.reshape(-1).astype(bool)
        prev_pts = points[status]
        curr_pts = tracked[status]
        if len(prev_pts) < 10:
            return 0.0, 0.0, 0.0

        matrix, _ = cv2.estimateAffinePartial2D(prev_pts, curr_pts)
        if matrix is None:
            return 0.0, 0.0, 0.0

        dx = float(matrix[0, 2])
        dy = float(matrix[1, 2])
        da = float(np.arctan2(matrix[1, 0], matrix[0, 0]))
        return dx, dy, da
