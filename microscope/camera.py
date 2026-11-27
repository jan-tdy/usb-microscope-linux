import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage


def apply_zoom(frame, zoom):
    if zoom <= 1.0:
        return frame
    height, width = frame.shape[:2]
    new_width, new_height = int(width / zoom), int(height / zoom)
    x0 = (width - new_width) // 2
    y0 = (height - new_height) // 2
    cropped = frame[y0:y0 + new_height, x0:x0 + new_width]
    return cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)


def draw_grid(frame, divisions=4, color=(0, 255, 0)):
    height, width = frame.shape[:2]
    for i in range(1, divisions):
        x = width * i // divisions
        y = height * i // divisions
        cv2.line(frame, (x, 0), (x, height), color, 1)
        cv2.line(frame, (0, y), (width, y), color, 1)


def draw_crosshair(frame, color=(0, 0, 255), size=20):
    height, width = frame.shape[:2]
    cx, cy = width // 2, height // 2
    cv2.line(frame, (cx - size, cy), (cx + size, cy), color, 1)
    cv2.line(frame, (cx, cy - size), (cx, cy + size), color, 1)


def can_capture(device_path, attempts=5):
    """Whether this device node actually delivers video frames.

    Some UVC cameras expose a second /dev/videoN node for metadata only
    (no image data) alongside their real capture node; opening it
    "succeeds" but every read() fails, so a few read attempts tell them apart.
    """
    cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap.release()
        return False
    ok = False
    for _ in range(attempts):
        ok, _ = cap.read()
        if ok:
            break
    cap.release()
    return ok


def to_qimage(frame_bgr):
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb.shape
    bytes_per_line = channels * width
    # .copy() detaches the QImage from rgb's buffer, which the next loop
    # iteration overwrites before Qt would otherwise get around to using it.
    return QImage(rgb.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()


class CameraWorker(QThread):
    frame_ready = pyqtSignal(QImage)
    error = pyqtSignal(str)
    snapshot_saved = pyqtSignal(str)
    recording_started = pyqtSignal(str)
    recording_stopped = pyqtSignal(str)

    def __init__(self, device_path, parent=None):
        super().__init__(parent)
        self.device_path = device_path
        self.zoom = 1.0
        self.show_grid = False
        self.show_crosshair = False
        self._running = False
        self._writer = None
        self._record_path = None
        self._pending_record_start = None
        self._pending_record_stop = False
        self._pending_snapshot_path = None

    def request_snapshot(self, path):
        self._pending_snapshot_path = path

    def request_recording_start(self, path):
        self._pending_record_start = path

    def request_recording_stop(self):
        self._pending_record_stop = True

    def stop(self):
        self._running = False

    def run(self):
        cap = cv2.VideoCapture(self.device_path, cv2.CAP_V4L2)
        if not cap.isOpened():
            self.error.emit(f"Could not open {self.device_path}")
            return
        self._running = True
        try:
            while self._running:
                ok, frame = cap.read()
                if not ok:
                    self.error.emit(f"Lost signal from {self.device_path}")
                    break
                frame = apply_zoom(frame, self.zoom)
                self._handle_pending_recording(cap, frame)
                self._handle_pending_snapshot(frame)
                if self._writer is not None:
                    self._writer.write(frame)
                display = frame.copy()
                if self.show_grid:
                    draw_grid(display)
                if self.show_crosshair:
                    draw_crosshair(display)
                self.frame_ready.emit(to_qimage(display))
        finally:
            if self._writer is not None:
                self._writer.release()
                self._writer = None
            cap.release()

    def _handle_pending_recording(self, cap, frame):
        if self._pending_record_start is not None:
            path = self._pending_record_start
            self._pending_record_start = None
            height, width = frame.shape[:2]
            fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
            if not writer.isOpened():
                self.error.emit(f"Failed to start recording to {path}")
            else:
                self._writer = writer
                self._record_path = path
                self.recording_started.emit(path)
        if self._pending_record_stop:
            self._pending_record_stop = False
            if self._writer is not None:
                self._writer.release()
                self._writer = None
                path, self._record_path = self._record_path, None
                self.recording_stopped.emit(path or "")

    def _handle_pending_snapshot(self, frame):
        if self._pending_snapshot_path is None:
            return
        path = self._pending_snapshot_path
        self._pending_snapshot_path = None
        if cv2.imwrite(path, frame):
            self.snapshot_saved.emit(path)
        else:
            self.error.emit(f"Failed to save snapshot to {path}")
