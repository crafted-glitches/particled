from pathlib import Path
import json

from particled.config import Config
from particled.visuals import param_panels


def test_particle_slider_range_supports_20k():
    sections = param_panels.sections_for("Particle Cloud", "Impact")
    particle_slider = sections[0].sliders[0]

    assert particle_slider.attr == "num_particles"
    assert particle_slider.hi == 20000


def test_save_and_load_preset_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(param_panels, "_PRESET_DIR", tmp_path)

    cfg = Config()
    cfg.num_particles = 1234
    cfg.band1_particle_count_scale = 1.7

    saved_path = param_panels.save_preset(cfg, "Particle Cloud", "Impact", "my live preset")
    assert saved_path.exists()
    assert saved_path.name == "my_live_preset.json"

    cfg.num_particles = 999
    cfg.band1_particle_count_scale = 0.2

    result = param_panels.load_preset(cfg, "Particle Cloud", "Impact", "my live preset")

    assert result["applied"] > 0
    assert cfg.num_particles == 1234
    assert cfg.band1_particle_count_scale == 1.7


def test_sections_and_defaults_cover_styles_and_modes():
    assert len(param_panels.sections_for("Torus Knot", None)) >= 2
    assert len(param_panels.sections_for("Penrose", None)) >= 2
    assert len(param_panels.sections_for("Particle Cloud", "Impact")) >= 4
    assert len(param_panels.sections_for("Particle Cloud", "Gravitas")) >= 5

    assert "knot_mu" in param_panels.defaults_for("Torus Knot", None)
    assert "penrose_triangle_scale" in param_panels.defaults_for("Penrose", None)
    assert "gravitas_push_strength" in param_panels.defaults_for("Particle Cloud", "Gravitas")


def test_load_preset_skips_unknown_values(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(param_panels, "_PRESET_DIR", tmp_path)

    payload = {
        "name": "custom",
        "style": "Particle Cloud",
        "mode": "Impact",
        "values": {
            "num_particles": 4321,
            "not_a_real_setting": 999,
        },
    }
    (tmp_path / "custom.json").write_text(json.dumps(payload), encoding="utf-8")

    cfg = Config()
    result = param_panels.load_preset(cfg, "Particle Cloud", "Impact", "custom")

    assert cfg.num_particles == 4321
    assert result == {"applied": 1, "skipped": 1}
