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


def _parse_list_devices(output):
    """Map /dev/videoN -> the camera's card name, from `v4l2-ctl --list-devices`.

    Its output groups device nodes under a header line per physical camera
    (e.g. "USB2.0 UVC PC Camera: USB2.0 UV (usb-0000:00:14.0-7):"), followed
    by that camera's indented /dev/videoN and /dev/mediaN nodes.
    """
    mapping = {}
    current_name = None
    for line in output.splitlines():
        if not line.strip():
            current_name = None
            continue
        if line.startswith(("\t", " ")):
            path = line.strip()
            if current_name and path.startswith("/dev/video"):
                mapping[path] = current_name
        else:
            current_name = line.split(":", 1)[0].strip()
    return mapping


def list_devices():
    if not is_available():
        return {}
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if result.returncode != 0:
        return {}
    return _parse_list_devices(result.stdout)


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
