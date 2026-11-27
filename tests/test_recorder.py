import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from microscope.recorder import FfmpegRecorder, ffmpeg_available  # noqa: E402

pytestmark = pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg is not installed")


def test_ffmpeg_recorder_produces_playable_h264(tmp_path):
    path = str(tmp_path / "out.mp4")
    recorder = FfmpegRecorder(path, width=64, height=48, fps=10)
    assert recorder.isOpened()

    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    for i in range(15):
        frame[:] = (i * 10) % 256
        recorder.write(frame)
    recorder.release()

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name", "-of", "csv=p=0", path],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert "h264" in result.stdout
    assert recorder.failed is False


def test_ffmpeg_recorder_reports_failure_when_encoder_cannot_write(tmp_path):
    # ffmpeg can't create a file in a directory that doesn't exist, so it
    # exits with a non-zero status — this must surface as recorder.failed,
    # not silently look like a normal, successful recording.
    bad_path = str(tmp_path / "no_such_dir" / "out.mp4")
    recorder = FfmpegRecorder(bad_path, width=64, height=48, fps=10)

    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    for _ in range(5):
        recorder.write(frame)
    recorder.release()

    assert recorder.failed is True
