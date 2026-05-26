from particled.config import Config


def test_particle_band_scale_helpers_match_band_count():
    cfg = Config(audio_band_count=6)

    cfg.band1_particle_count_scale = 0.5
    cfg.band6_particle_count_scale = 1.8
    cfg.band1_particle_size_scale = 0.8
    cfg.band6_particle_size_scale = 2.2

    count_scales = cfg.get_particle_band_count_scales()
    size_scales = cfg.get_particle_band_size_scales()

    assert len(count_scales) == 6
    assert len(size_scales) == 6
    assert count_scales[0] == 0.5
    assert count_scales[-1] == 1.8
    assert size_scales[0] == 0.8
    assert size_scales[-1] == 2.2
