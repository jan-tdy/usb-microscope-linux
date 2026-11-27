# usb-microscope-linux

A PyQt5 app for cheap USB ~800x microscope cameras on Linux.

These microscopes are plain UVC (USB Video Class) webcams, so this app
talks to any `/dev/video*` device over the standard Linux v4l2 interface
— it isn't tied to one specific model, and it doesn't use or depend on
any vendor's Windows-only bundled software.

## Features

- Live video stream from any detected `/dev/video*` device, with a
  device dropdown and refresh button. The dropdown shows each camera's
  name (e.g. "USB2.0 UVC PC Camera (/dev/video2)") and skips device
  nodes that don't actually deliver a video frame — some UVC cameras
  expose a second metadata-only node alongside their real one, which
  this app no longer makes you guess between
- Digital zoom (software crop + upscale), always available regardless
  of what the camera itself exposes
- Auto-detected hardware controls: if the connected camera exposes an
  LED/illumination control, a hardware zoom control, or other `v4l2`
  controls (brightness, contrast, exposure, white balance, ...), the
  matching sliders/checkboxes/dropdowns appear automatically — nothing
  is hard-coded to one microscope model. This includes menu-type
  controls like `exposure_auto`, so you can switch a camera to manual
  exposure and dial the exposure time down — the actual fix for motion
  blur from vibration at high magnification, which no amount of
  post-capture frame alignment can undo. If a camera exposes none of
  these (most cheap clones only have a physical LED wheel and a
  mechanical focus ring), the app says so instead of showing dead
  controls. After every change the app reads the value straight back
  from the camera and says so in the status bar — some cheap UVC chips
  accept a control write but never actually apply it, and this tells
  that apart from the app failing to set it.
- Snapshot (PNG) and video recording (MP4), saved under a configurable
  folder (defaults to `~/Pictures/USBMicroscope`). Recording uses the
  system `ffmpeg` binary to encode real H.264 — the far more widely
  playable codec most phones, browsers and messaging apps expect.
  Without `ffmpeg` installed it falls back to OpenCV's own MPEG-4 Part 2
  ("mp4v") encoder, whose files are valid but many apps refuse to open
- Crosshair and grid overlays for quick visual alignment while looking
  at a specimen
- Vibration compensation: an optional digital stabilizer that cancels
  small frame-to-frame shake (e.g. from a wobbly desk or handheld
  stand) without fighting a deliberate, sustained move of the
  microscope. Off by default — toggle it in the "Stabilization" group
- Image rotation (0-359°, plus one-click 0/90/180/270° snap buttons) to
  correct however the camera happens to be mounted
- Point-to-point measurement: calibrate once by clicking two points of
  a known real-world distance apart (e.g. along a ruler) and entering
  that distance, then click any two points on the image to read off
  the real-world distance between them, drawn directly on the video.
  Calibration automatically accounts for the digital zoom level active
  at measurement time versus at calibration time — it does *not*
  account for changing the camera's own optical zoom or focus
  distance, which needs a fresh calibration
- Settings (device, zoom, rotation, overlays, stabilization, unit, save
  folder, calibration) are remembered between runs, under
  `$XDG_CONFIG_HOME/usb-microscope-linux/settings.json`
  (`~/.config/usb-microscope-linux/settings.json` by default)

## Requirements

- Linux with a UVC-compatible USB microscope/webcam
- Python 3.8+
- `v4l-utils` (system package, optional — only needed for the hardware
  control panel; the app runs fine without it, just without those
  sliders)
- `ffmpeg` (system package, optional but strongly recommended — without
  it, recorded videos use a codec many players can't open; see above)

```bash
sudo apt install v4l-utils ffmpeg   # Debian/Ubuntu/Mint
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
