import re
import shutil
import subprocess

_CTRL_LINE_RE = re.compile(
    r"^\s*(?P<name>[a-zA-Z0-9_]+)\s+0x[0-9a-fA-F]+\s+"
    r"\((?P<type>int|bool|menu|int64|string|bitmask)\)\s*:(?P<rest>.*)$"
)
_ATTR_RE = re.compile(r"(\w+)=(-?\d+)")
_MENU_ITEM_RE = re.compile(r"^\s+(\d+):\s*(.+?)\s*$")


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
        if match:
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
                    "menu_items": {},
                }
            )
            continue
        # A "menu" control's named options (e.g. exposure_auto's "Manual
        # Mode", "Aperture Priority Mode", ...) are listed as indented
        # "<value>: <label>" lines directly under it, only with
        # --list-ctrls-menus — never on their own, so they belong to
        # whichever control line came immediately before.
        if controls and controls[-1]["type"] == "menu":
            menu_match = _MENU_ITEM_RE.match(line)
            if menu_match:
                controls[-1]["menu_items"][int(menu_match.group(1))] = menu_match.group(2)
    return controls


def list_controls(device_path):
    if not is_available():
        return []
    try:
        result = subprocess.run(
            ["v4l2-ctl", "-d", device_path, "--list-ctrls-menus"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            # Older v4l-utils versions don't have --list-ctrls-menus; fall
            # back to plain controls (menu controls just won't show up).
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


def _parse_get_ctrl(output):
    match = re.search(r":\s*(-?\d+)", output)
    return int(match.group(1)) if match else None


def get_control(device_path, name):
    """Read a control's current value straight back from the device.

    Used right after set_control() to tell a real app bug (the write
    failed or didn't stick) apart from a camera that accepts the ioctl
    but silently ignores it — common on cheap UVC chips whose firmware
    doesn't actually wire a listed control to anything.
    """
    try:
        result = subprocess.run(
            ["v4l2-ctl", "-d", device_path, "--get-ctrl", name],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return _parse_get_ctrl(result.stdout)
