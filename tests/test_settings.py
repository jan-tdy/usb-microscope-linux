import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from microscope import settings  # noqa: E402


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    data = {"zoom": 2.5, "rotation": 90, "calibration": {"pixels_per_unit": 12.3, "unit": "mm"}}
    assert settings.save_settings(data) is True
    assert settings.load_settings() == data


def test_load_settings_returns_empty_dict_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert settings.load_settings() == {}


def test_load_settings_returns_empty_dict_on_corrupt_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    path = Path(settings.settings_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not valid json", encoding="utf-8")

    assert settings.load_settings() == {}


def test_settings_path_is_under_xdg_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    assert settings.settings_path().startswith(str(tmp_path))
    assert settings.settings_path().endswith("settings.json")
