import glob
import re

_INDEX_RE = re.compile(r"(\d+)$")


def _sort_key(path):
    match = _INDEX_RE.search(path)
    return int(match.group(1)) if match else 0


def list_video_devices():
    return sorted(glob.glob("/dev/video*"), key=_sort_key)
