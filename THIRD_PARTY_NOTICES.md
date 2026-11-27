# Third-party notices

This project's own source code is MIT-licensed (see `LICENSE`). It is not
bundled with any of the libraries below — they are ordinary dependencies
you install yourself (`pip`/`apt`), and each keeps its own license:

| Dependency | License | How it's used |
|---|---|---|
| PyQt5 | GPLv3, or Riverbank Computing's commercial license | UI toolkit |
| OpenCV (`opencv-python`) | Apache License 2.0 | Video capture, image processing, recording |
| NumPy | BSD 3-Clause | Pulled in by OpenCV for frame arrays |
| v4l-utils (`v4l2-ctl`) | GPLv2 | Invoked as an external command, never linked into this program |
| ffmpeg | GPL (a standard distro build with libx264 enabled, as used here, is GPL rather than LGPL) | Invoked as an external command for H.264 video recording, never linked into this program |

**PyQt5 note:** PyQt5 is GPLv3 (or a paid Riverbank commercial license),
not MIT. Depending on it as an external library, as this project does,
does not change this project's own MIT license. If you ever package a
bundled binary that statically links PyQt5 into this program, that
combined work must itself comply with GPLv3 (or you need a commercial
PyQt5 license) — that only applies to such a bundled build, not to
running this script against a separately-installed PyQt5. If that
licensing shape doesn't suit your use case, the LGPL-licensed
PySide2/PySide6 is a drop-in-ish alternative; this project uses PyQt5
because that's what was asked for.

No text, images, or code from any microscope manufacturer's manual or
product page is included in or was used to write this project. The
camera is accessed only through the Linux kernel's standard UVC/v4l2
interfaces, which are hardware-independent — nothing here is specific to
one ASIN or vendor.
