# usb-microscope-linux

A PyQt5 app for cheap USB ~800x microscope cameras on Linux.

These microscopes are plain UVC (USB Video Class) webcams, so this app
talks to any `/dev/video*` device over the standard Linux v4l2 interface
— it isn't tied to one specific model, and it doesn't use or depend on
any vendor's Windows-only bundled software.

## Features

- Live video stream from any detected `/dev/video*` device, with a
  device dropdown and refresh button
- Digital zoom (software crop + upscale), always available regardless
  of what the camera itself exposes
- Auto-detected hardware controls: if the connected camera exposes an
  LED/illumination control, a hardware zoom control, or other `v4l2`
  controls (brightness, contrast, white balance, ...), the matching
  sliders/checkboxes appear automatically — nothing is hard-coded to one
  microscope model. If a camera exposes none of these (most cheap clones
  only have a physical LED wheel and a mechanical focus ring), the app
  says so instead of showing dead controls.
- Snapshot (PNG) and video recording (MP4), saved under a configurable
  folder (defaults to `~/Pictures/USBMicroscope`)
- Crosshair and grid overlays for quick visual alignment while looking
  at a specimen

## Requirements

- Linux with a UVC-compatible USB microscope/webcam
- Python 3.8+
- `v4l-utils` (system package, optional — only needed for the hardware
  control panel; the app runs fine without it, just without those
  sliders)

```bash
sudo apt install v4l-utils          # Debian/Ubuntu/Mint
python3 -m pip install --user -r requirements.txt
```

## Running

```bash
python3 usb_microscope.py
```

## Development

```bash
python3 -m pip install --user -r requirements-dev.txt
pytest
```

## Licensing

This project's own code is MIT-licensed (see `LICENSE`). It depends on
third-party libraries under their own, different licenses — most
notably PyQt5, which is GPLv3/commercial rather than MIT. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for the full
breakdown and what that means if you redistribute a bundled build.

## Code Master

This repo ships a [`codemaster-metadata.json`](codemaster-metadata.json)
so it can be listed and installed from
[Jadiv Code Master](https://github.com/jan-tdy/codemaster)'s app store.
