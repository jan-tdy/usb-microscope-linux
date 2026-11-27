import os
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import v4l2_controls
from .camera import CameraWorker, can_capture
from .devices import list_video_devices

CAPTURE_DIR = os.path.join(os.path.expanduser("~"), "Pictures", "USBMicroscope")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB Microscope")
        self.worker = None
        self._recording = False
        self._device_path = None
        self._build_ui()
        self._refresh_devices()

    # -- UI construction ---------------------------------------------------- #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        self.video_label = QLabel("No signal")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: black; color: gray;")
        root.addWidget(self.video_label, 1)

        side = QVBoxLayout()
        root.addLayout(side)

        device_row = QHBoxLayout()
        self.device_combo = QComboBox()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._refresh_devices)
        device_row.addWidget(self.device_combo)
        device_row.addWidget(refresh_button)
        side.addLayout(device_row)

        self.stream_button = QPushButton("Start Stream")
        self.stream_button.clicked.connect(self._toggle_stream)
        side.addWidget(self.stream_button)

        zoom_box = QGroupBox("Digital Zoom")
        zoom_layout = QVBoxLayout(zoom_box)
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 40)
        self.zoom_slider.setValue(10)
        self.zoom_value_label = QLabel("1.0x")
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_value_label)
        side.addWidget(zoom_box)

        overlay_box = QGroupBox("Overlay")
        overlay_layout = QVBoxLayout(overlay_box)
        self.crosshair_check = QCheckBox("Crosshair")
        self.grid_check = QCheckBox("Grid")
        self.crosshair_check.toggled.connect(self._on_crosshair_toggled)
        self.grid_check.toggled.connect(self._on_grid_toggled)
        overlay_layout.addWidget(self.crosshair_check)
        overlay_layout.addWidget(self.grid_check)
        side.addWidget(overlay_box)

        stabilize_box = QGroupBox("Stabilization")
        stabilize_layout = QVBoxLayout(stabilize_box)
        self.stabilize_check = QCheckBox("Vibration compensation")
        self.stabilize_check.setToolTip(
            "Digitally cancels small shake/jitter frame-to-frame (e.g. from a\n"
            "desk or handheld stand). Doesn't fight a deliberate, sustained\n"
            "move of the microscope, and costs some CPU per frame."
        )
        self.stabilize_check.toggled.connect(self._on_stabilize_toggled)
        stabilize_layout.addWidget(self.stabilize_check)
        side.addWidget(stabilize_box)

        self.hw_controls_container = QVBoxLayout()
        side.addLayout(self.hw_controls_container)

        capture_row = QHBoxLayout()
        self.snapshot_button = QPushButton("Snapshot")
        self.snapshot_button.clicked.connect(self._take_snapshot)
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self._toggle_recording)
        capture_row.addWidget(self.snapshot_button)
        capture_row.addWidget(self.record_button)
        side.addLayout(capture_row)

        save_row = QHBoxLayout()
        save_row.addWidget(QLabel("Save folder:"))
        self.save_dir_label = QLabel(CAPTURE_DIR)
        self.save_dir_label.setWordWrap(True)
        change_dir_button = QPushButton("Change…")
        change_dir_button.clicked.connect(self._change_save_dir)
        save_row.addWidget(self.save_dir_label, 1)
        save_row.addWidget(change_dir_button)
        side.addLayout(save_row)

        side.addStretch(1)
        self._save_dir = CAPTURE_DIR

        self.statusBar().showMessage("Ready")

    # -- device / stream lifecycle -------------------------------------------- #

    def _refresh_devices(self):
        self.device_combo.clear()
        names = v4l2_controls.list_devices()
        usable = []
        for path in list_video_devices():
            # Skip probing the device the running worker already has open —
            # opening it a second time here would fight it for the camera.
            if (self.worker is not None and path == self._device_path) or can_capture(path):
                usable.append(path)
        for path in usable:
            label = f"{names[path]} ({path})" if path in names else path
            self.device_combo.addItem(label, path)
        if not usable:
            self.statusBar().showMessage("No usable /dev/video* capture devices found")

    def _toggle_stream(self):
        if self.worker is None:
            self._start_stream()
        else:
            self._stop_stream()

    def _start_stream(self):
        device_path = self.device_combo.currentData()
        if not device_path:
            QMessageBox.warning(self, "No device", "No camera device selected.")
            return

        self.worker = CameraWorker(device_path)
        self.worker.zoom = self.zoom_slider.value() / 10.0
        self.worker.show_grid = self.grid_check.isChecked()
        self.worker.show_crosshair = self.crosshair_check.isChecked()
        self.worker.stabilize = self.stabilize_check.isChecked()
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.error.connect(self._on_worker_error)
        self.worker.snapshot_saved.connect(self._on_snapshot_saved)
        self.worker.recording_started.connect(self._on_recording_started)
        self.worker.recording_stopped.connect(self._on_recording_stopped)
        self.worker.start()

        self.stream_button.setText("Stop Stream")
        self.device_combo.setEnabled(False)
        self._device_path = device_path
        self._build_hardware_controls(device_path)
        self.statusBar().showMessage(f"Streaming from {device_path}")

    def _stop_stream(self):
        if self.worker is None:
            return
        was_recording = self._recording
        if was_recording:
            self.worker.request_recording_stop()
        self.worker.stop()
        # Finalizing an ffmpeg-backed recording (closing its moov atom) can
        # take a bit longer than plain capture teardown, so give it more room.
        self.worker.wait(8000 if was_recording else 2000)
        self.worker = None
        self._recording = False
        self.record_button.setText("Start Recording")
        self.stream_button.setText("Start Stream")
        self.device_combo.setEnabled(True)
        self.video_label.setText("No signal")
        self.video_label.setPixmap(QPixmap())
        self.statusBar().showMessage("Stream stopped")

    def _on_frame(self, qimage):
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled)

    def _on_worker_error(self, message):
        self.statusBar().showMessage(message)
        if "Could not open" in message or "Lost signal" in message:
            self._stop_stream()

    # -- digital zoom / overlay ---------------------------------------------- #

    def _on_zoom_changed(self, value):
        zoom = value / 10.0
        self.zoom_value_label.setText(f"{zoom:.1f}x")
        if self.worker is not None:
            self.worker.zoom = zoom

    def _on_crosshair_toggled(self, checked):
        if self.worker is not None:
            self.worker.show_crosshair = checked

    def _on_grid_toggled(self, checked):
        if self.worker is not None:
            self.worker.show_grid = checked

    def _on_stabilize_toggled(self, checked):
        if self.worker is not None:
            self.worker.set_stabilize(checked)

    # -- hardware (v4l2) controls --------------------------------------------- #

    @staticmethod
    def _classify(name):
        lname = name.lower()
        if any(keyword in lname for keyword in ("led", "light", "illum", "backlight")):
            return "led"
        if "zoom" in lname:
            return "zoom"
        return "other"

    def _build_hardware_controls(self, device_path):
        self._clear_layout(self.hw_controls_container)

        if not v4l2_controls.is_available():
            self.hw_controls_container.addWidget(
                QLabel("v4l2-ctl not found — install v4l-utils for hardware LED/zoom control.")
            )
            return

        controls = [
            c
            for c in v4l2_controls.list_controls(device_path)
            if c["type"] in ("int", "bool") or (c["type"] == "menu" and c["menu_items"])
        ]
        led_controls = [c for c in controls if self._classify(c["name"]) == "led"]
        zoom_controls = [c for c in controls if self._classify(c["name"]) == "zoom"]
        other_controls = [c for c in controls if self._classify(c["name"]) == "other"]

        led_group = QGroupBox("LED / Illumination")
        led_layout = QVBoxLayout(led_group)
        if led_controls:
            for control in led_controls:
                led_layout.addWidget(self._make_control_widget(control))
        else:
            led_layout.addWidget(QLabel("No LED control exposed — use the physical ring/wheel if present."))
        self.hw_controls_container.addWidget(led_group)

        if zoom_controls:
            zoom_group = QGroupBox("Hardware Zoom")
            zoom_layout = QVBoxLayout(zoom_group)
            for control in zoom_controls:
                zoom_layout.addWidget(self._make_control_widget(control))
            self.hw_controls_container.addWidget(zoom_group)

        if other_controls:
            other_group = QGroupBox("Other Camera Controls")
            other_layout = QVBoxLayout(other_group)
            for control in other_controls:
                other_layout.addWidget(self._make_control_widget(control))
            self.hw_controls_container.addWidget(other_group)

    def _make_control_widget(self, control):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(control["name"].replace("_", " ")))

        if control["type"] == "bool":
            checkbox = QCheckBox()
            checkbox.setChecked(bool(control["value"]))
            checkbox.toggled.connect(
                lambda checked, name=control["name"]: self._set_hw_control(name, int(checked))
            )
            layout.addWidget(checkbox)
        elif control["type"] == "menu":
            combo = QComboBox()
            current_index = 0
            for index, (item_value, label) in enumerate(sorted(control["menu_items"].items())):
                combo.addItem(label, item_value)
                if item_value == control["value"]:
                    current_index = index
            combo.setCurrentIndex(current_index)
            combo.currentIndexChanged.connect(
                lambda index, c=combo, name=control["name"]: self._set_hw_control(name, c.itemData(index))
            )
            layout.addWidget(combo)
        else:
            slider = QSlider(Qt.Horizontal)
            slider.setRange(control["min"] or 0, control["max"] or 100)
            slider.setSingleStep(control["step"] or 1)
            initial = control["value"] if control["value"] is not None else (control["default"] or 0)
            slider.setValue(initial)
            value_label = QLabel(str(initial))
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(str(v)))
            slider.sliderReleased.connect(
                lambda name=control["name"], s=slider: self._set_hw_control(name, s.value())
            )
            layout.addWidget(slider)
            layout.addWidget(value_label)

        return container

    def _set_hw_control(self, name, value):
        if not v4l2_controls.set_control(self._device_path, name, value):
            self.statusBar().showMessage(f"Failed to set {name}")
            return
        # Read the value straight back: some cheap UVC cameras accept a
        # control write (ioctl succeeds) but their firmware never actually
        # applies it — reporting the real post-write value tells that
        # apart from an app-side bug, instead of just assuming success.
        actual = v4l2_controls.get_control(self._device_path, name)
        if actual is not None and actual != value:
            self.statusBar().showMessage(
                f"{name}: set to {value}, but camera still reports {actual} "
                "— this camera may be ignoring that control"
            )
        else:
            self.statusBar().showMessage(f"Set {name} = {value}")

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    # -- snapshot / recording -------------------------------------------------- #

    def _change_save_dir(self):
        chosen = QFileDialog.getExistingDirectory(self, "Choose save folder", self._save_dir)
        if chosen:
            self._save_dir = chosen
            self.save_dir_label.setText(chosen)

    def _take_snapshot(self):
        if self.worker is None:
            QMessageBox.information(self, "Not streaming", "Start the stream before taking a snapshot.")
            return
        os.makedirs(self._save_dir, exist_ok=True)
        filename = f"snapshot_{datetime.now():%Y%m%d_%H%M%S}.png"
        self.worker.request_snapshot(os.path.join(self._save_dir, filename))

    def _on_snapshot_saved(self, path):
        self.statusBar().showMessage(f"Snapshot saved: {path}")

    def _toggle_recording(self):
        if self.worker is None:
            QMessageBox.information(self, "Not streaming", "Start the stream before recording.")
            return
        if not self._recording:
            os.makedirs(self._save_dir, exist_ok=True)
            filename = f"recording_{datetime.now():%Y%m%d_%H%M%S}.mp4"
            self.worker.request_recording_start(os.path.join(self._save_dir, filename))
        else:
            self.worker.request_recording_stop()

    def _on_recording_started(self, path):
        self._recording = True
        self.record_button.setText("Stop Recording")
        self.statusBar().showMessage(f"Recording to {path}")

    def _on_recording_stopped(self, path):
        self._recording = False
        self.record_button.setText("Start Recording")
        self.statusBar().showMessage(f"Recording saved: {path}" if path else "Recording stopped")

    # -- window lifecycle -------------------------------------------------- #

    def closeEvent(self, event):
        self._stop_stream()
        event.accept()
