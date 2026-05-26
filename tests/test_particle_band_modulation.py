import numpy as np

from particled.config import Config
from particled.visuals.particle_cloud.impact import ParticleCloudImpact


def test_band_modulation_controls_particle_count_and_size():
    cfg = Config(num_particles=2000, audio_band_count=8)
    for i in range(1, 9):
        setattr(cfg, f"band{i}_particle_count_scale", 0.0)
        setattr(cfg, f"band{i}_particle_size_scale", 1.0)

    cfg.band1_particle_count_scale = 1.0
    cfg.band1_particle_size_scale = 2.0

    field = ParticleCloudImpact(cfg)

    features = {"bands": (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)}
    keep_mask, size_mul = field._compute_band_modulation((0.0, 0.0, 0.0), features)

    band0 = field.band_index == 0
    other = field.band_index != 0

    assert np.all(keep_mask[band0])
    assert not np.any(keep_mask[other])
    assert float(np.mean(size_mul[band0])) > 2.5
    assert float(np.min(size_mul)) >= 0.05


def test_band_level_resolution_interpolates_and_fallbacks():
    cfg = Config(num_particles=300, audio_band_count=8)
    field = ParticleCloudImpact(cfg)

    interpolated = field._resolve_band_levels(
        (0.2, 0.4, 0.8),
        {"bands": (0.1, 0.5, 0.9, 0.3)},
    )
    assert len(interpolated) == 8
    assert float(interpolated[0]) >= 0.0
    assert float(interpolated[-1]) <= 1.5

    fallback = field._resolve_band_levels((0.2, 0.4, 0.8), None)
    assert len(fallback) == 8
    assert np.isclose(float(fallback[0]), 0.2)
    assert np.isclose(float(fallback[-1]), 0.8)


def test_compute_sizes_and_rotation_shapes():
    cfg = Config(num_particles=150)
    field = ParticleCloudImpact(cfg)

    x, y, z = field.base_x.copy(), field.base_y.copy(), field.base_z.copy()
    xr, yr, zr = field._apply_rotation(x, y, z, t=1.25)
    assert xr.shape == x.shape == yr.shape == zr.shape

    brightness = np.clip(np.linspace(0.0, 1.0, cfg.num_particles), 0.0, 1.0)
    sizes = field._compute_sizes(brightness)
    assert sizes.shape == brightness.shape
    assert float(np.min(sizes)) >= 0.0


def test_impact_sizes_increase_with_audio_level():
    cfg = Config(num_particles=120)
    field = ParticleCloudImpact(cfg)
    brightness = np.clip(np.linspace(0.2, 1.0, cfg.num_particles), 0.0, 1.0)

    quiet = field._compute_sizes_with_audio(brightness, audio_level=0.0)
    loud = field._compute_sizes_with_audio(brightness, audio_level=1.0)

    assert np.all(loud >= quiet)


def test_impact_draw_respects_band_count_gating():
    cfg = Config(num_particles=1200, audio_band_count=8)
    for i in range(1, 9):
        setattr(cfg, f"band{i}_particle_count_scale", 0.0)
        setattr(cfg, f"band{i}_particle_size_scale", 1.0)
    cfg.band1_particle_count_scale = 1.0

    field = ParticleCloudImpact(cfg)

    captured = {"n": None}

    def _capture_render(surface, xs, ys, brightness, sizes):
        captured["n"] = len(xs)

    field._render_points = _capture_render

    features = {"bands": (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)}
    field.draw(
        surface=None,
        t=0.2,
        audio_level=0.8,
        audio_bands=(0.8, 0.2, 0.1),
        audio_features=features,
    )

    expected = int(np.sum(field.band_index == 0))
    assert captured["n"] == expected
