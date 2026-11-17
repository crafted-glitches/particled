import numpy as np

from particled.config import Config
from particled.visuals.noise import fbm3, value_noise3
from particled.visuals.plexus import PlexusField


def test_base_nodes_are_unit_distance_from_center():
    x, y, z = PlexusField._build_base_nodes(500)
    radii = np.sqrt(x**2 + y**2 + z**2)

    assert x.shape == (500,)
    assert np.allclose(radii, 1.0, atol=1e-9)


def test_candidate_edges_have_no_self_loops_or_duplicates():
    x, y, z = PlexusField._build_base_nodes(200)
    edge_i, edge_j, mean_length = PlexusField._build_candidate_edges(
        x, y, z, k=5, chord_ratio=0.5
    )

    assert len(edge_i) > 0
    assert not np.any(edge_i == edge_j)

    pairs = set(zip(edge_i.tolist(), edge_j.tolist(), strict=True))
    assert len(pairs) == len(edge_i)
    assert all(a < b for a, b in pairs)
    assert mean_length > 0.0


def test_node_count_is_capped_for_performance():
    cfg = Config(num_particles=50000)
    field = PlexusField(cfg)

    assert field.node_count == PlexusField._MAX_NODES


def test_draw_invokes_render_lines_with_matching_endpoint_arrays():
    cfg = Config(num_particles=300)
    field = PlexusField(cfg)

    captured = {}

    def _capture(surface, x0, y0, x1, y1, b0, b1, width=1.0, alpha=1.0):
        captured["n"] = len(x0)
        captured["shapes"] = (
            x0.shape, y0.shape, x1.shape, y1.shape, b0.shape, b1.shape,
        )
        captured["width"] = width
        captured["alpha"] = alpha

    field._render_lines = _capture
    field.draw(surface=None, t=1.0, audio_level=0.2, audio_bands=(0.2, 0.2, 0.2))

    assert captured["n"] > 0
    shapes = captured["shapes"]
    assert all(s == (captured["n"],) for s in shapes)
    assert captured["width"] == cfg.plexus_edge_width
    assert captured["alpha"] == cfg.plexus_edge_base_alpha


def test_louder_audio_reveals_more_active_edges():
    def active_edge_count(audio_level: float) -> int:
        cfg = Config(num_particles=500)
        field = PlexusField(cfg)
        captured = {"n": 0}

        def _capture(surface, x0, y0, x1, y1, b0, b1, width=1.0, alpha=1.0):
            captured["n"] = len(x0)

        field._render_lines = _capture
        features = {"bands": (audio_level,) * 8, "transient": 0.0, "centroid": 0.3}
        field.draw(
            surface=None,
            t=2.0,
            audio_level=audio_level,
            audio_bands=(audio_level,) * 3,
            audio_features=features,
        )
        return captured["n"]

    quiet = active_edge_count(0.0)
    loud = active_edge_count(1.2)

    assert loud >= quiet


def test_transient_flash_boosts_brightness():
    cfg = Config(num_particles=400)
    field = PlexusField(cfg)

    captured = {}

    def _capture(surface, x0, y0, x1, y1, b0, b1, width=1.0, alpha=1.0):
        captured["mean_brightness"] = float(np.mean(np.concatenate([b0, b1])))

    field._render_lines = _capture

    field.draw(
        surface=None,
        t=1.0,
        audio_level=0.2,
        audio_bands=(0.2, 0.2, 0.2),
        audio_features={"bands": (0.2,) * 8, "transient": 0.0, "centroid": 0.2},
    )
    no_flash_brightness = captured["mean_brightness"]

    field.draw(
        surface=None,
        t=1.016,
        audio_level=0.2,
        audio_bands=(0.2, 0.2, 0.2),
        audio_features={"bands": (0.2,) * 8, "transient": 1.0, "centroid": 0.2},
    )
    flash_brightness = captured["mean_brightness"]

    assert flash_brightness > no_flash_brightness


def test_value_noise3_is_bounded_and_deterministic():
    pos = np.random.default_rng(0).uniform(-5.0, 5.0, size=(200, 3))
    n1 = value_noise3(pos, seed=42)
    n2 = value_noise3(pos, seed=42)
    n3 = value_noise3(pos, seed=7)

    assert np.array_equal(n1, n2)
    assert not np.array_equal(n1, n3)
    assert np.all(n1 >= -1.0) and np.all(n1 <= 1.0)


def test_fbm3_stays_bounded_across_octaves():
    pos = np.random.default_rng(1).uniform(-3.0, 3.0, size=(100, 3))
    for octaves in (1, 2, 4):
        values = fbm3(pos, octaves=octaves, seed=3)
        assert values.shape == (100,)
        assert np.all(values >= -1.0) and np.all(values <= 1.0)
