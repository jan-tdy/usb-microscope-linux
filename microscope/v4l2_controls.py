import re
import shutil
import subprocess

_CTRL_LINE_RE = re.compile(
    r"^\s*(?P<name>[a-zA-Z0-9_]+)\s+0x[0-9a-fA-F]+\s+"
    r"\((?P<type>int|bool|menu|int64|string|bitmask)\)\s*:(?P<rest>.*)$"
)
_ATTR_RE = re.compile(r"(\w+)=(-?\d+)")


def is_available():
    return shutil.which("v4l2-ctl") is not None


def _parse_list_ctrls(output):
    controls = []
    for line in output.splitlines():
        match = _CTRL_LINE_RE.match(line)
        if not match:
            continue
        attrs = {key: int(value) for key, value in _ATTR_RE.findall(match.group("rest"))}
        controls.append(
            {
                "name": match.group("name"),
                "type": match.group("type"),
                "min": attrs.get("min"),
                "max": attrs.get("max"),
                "step": attrs.get("step", 1),
                "default": attrs.get("default"),
                "value": attrs.get("value"),
            }
        )
    return controls


def list_controls(device_path):
    if not is_available():
        return []
    try:
        result = subprocess.run(
            ["v4l2-ctl", "-d", device_path, "--list-ctrls"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return _parse_list_ctrls(result.stdout)


def set_control(device_path, name, value):
    try:
        result = subprocess.run(
            ["v4l2-ctl", "-d", device_path, "--set-ctrl", f"{name}={value}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0
