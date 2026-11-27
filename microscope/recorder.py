import shutil
import subprocess


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


class FfmpegRecorder:
    """Pipes raw frames to the system `ffmpeg` binary to encode H.264/MP4.

    OpenCV's own bundled ffmpeg (inside the opencv-python wheel) has no
    H.264 encoder, so cv2.VideoWriter can only write MPEG-4 Part 2
    ("mp4v") video — a codec many phones, browsers and messaging apps
    simply refuse to open, even though the file itself isn't corrupt.
    A system ffmpeg install (almost always built with libx264) produces
    H.264 instead, which is about as universally playable as video gets.
    Exposes the same write()/release()/isOpened() shape as
    cv2.VideoWriter so callers don't need to care which one they have.
    """

    def __init__(self, path, width, height, fps):
        self.path = path
        self.failed = False
        self._process = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-f", "rawvideo",
                "-pixel_format", "bgr24",
                "-video_size", f"{width}x{height}",
                "-framerate", str(fps),
                "-i", "-",
                "-an",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "veryfast",
                "-movflags", "+faststart",
                path,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def isOpened(self):
        return self._process.poll() is None

    def write(self, frame):
        try:
            self._process.stdin.write(frame.tobytes())
        except (BrokenPipeError, OSError):
            # ffmpeg exited on its own (bad args, disk full, ...) — note
            # it so release() and the caller can tell this recording
            # didn't actually finish writing a valid file.
            self.failed = True

    def release(self):
        if self._process.stdin is not None:
            try:
                self._process.stdin.close()
            except OSError:
                pass
        try:
            # -movflags +faststart makes ffmpeg do a second pass over the
            # whole file to move its index to the front, which "can take a
            # while" on a large recording (per ffmpeg's own docs) — killing
            # it too early leaves a truncated, unplayable file, exactly what
            # this recorder exists to avoid. 30s comfortably covers a
            # typical multi-minute microscope clip without hanging forever
            # on a truly stuck process.
            self._process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        if self._process.returncode != 0:
            self.failed = True
