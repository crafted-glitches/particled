"""Per-style overlay panel definitions.

Maps every CLI-configurable parameter to a SliderDef for each style/mode,
then assembles them into an OverlayPanel ready to attach to main.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from particled.config import Config
from particled.visuals.overlay import OverlayPanel, SectionDef, SliderDef

# ── shared sections ────────────────────────────────────────────────────────────

_COMMON = SectionDef(
    title="Common",
    sliders=[
        SliderDef("Particles",        "num_particles",    100,  20000, 100,   "{:.0f}"),
        SliderDef("Point size",       "max_point_size",   1.0,   12.0,  0.1,  "{:.1f}"),
        SliderDef("Fade / trails",    "fade_alpha",         0,     255,   1,   "{:.0f}"),
        SliderDef("Brightness gamma", "brightness_gamma",  0.5,   3.0,  0.05, "{:.2f}"),
        SliderDef("Audio gain",       "audio_gain",         0.0, 200.0,  1.0, "{:.1f}"),
    ],
)

_CLOUD_MOTION = SectionDef(
    title="Cloud motion",
    sliders=[
        SliderDef("Density sigma",   "cloud_density_sigma",  0.1,  5.0, 0.05, "{:.2f}"),
        SliderDef("Drift speed",     "cloud_drift_speed",    0.0,  1.0, 0.01, "{:.2f}"),
        SliderDef("Breath speed",    "cloud_breath_speed",   0.0,  2.0, 0.02, "{:.2f}"),
        SliderDef("Rotation Y",      "cloud_rotation_speed_y", 0.0, 0.5, 0.005, "{:.3f}"),
        SliderDef("Rotation X",      "cloud_rotation_speed_x", 0.0, 0.5, 0.005, "{:.3f}"),
    ],
)

_CLOUD_AUDIO = SectionDef(
    title="Audio reactivity",
    sliders=[
        SliderDef("Noise threshold",  "audio_noise_threshold",  0.0, 0.5,  0.005, "{:.3f}"),
        SliderDef("Transient sens",   "audio_transient_sensitivity", 0.2, 5.0, 0.05, "{:.2f}"),
        SliderDef("Drift boost",      "cloud_audio_drift_boost", 0.0, 1.0, 0.01,  "{:.2f}"),
        SliderDef("Breath boost",     "cloud_audio_breath_boost", 0.0, 1.0, 0.01, "{:.2f}"),
        SliderDef("Size boost",       "cloud_audio_size_boost",  0.0, 1.0, 0.01,  "{:.2f}"),
    ],
)


def _build_band_mapping_section(max_bands: int = 8) -> SectionDef:
    sliders: list[SliderDef] = []
    for i in range(1, max_bands + 1):
        sliders.append(
            SliderDef(
                f"Band {i} count",
                f"band{i}_particle_count_scale",
                0.0,
                2.0,
                0.02,
                "{:.2f}",
            )
        )
        sliders.append(
            SliderDef(
                f"Band {i} size",
                f"band{i}_particle_size_scale",
                0.2,
                3.0,
                0.02,
                "{:.2f}",
            )
        )
    return SectionDef(title="Band mapping", sliders=sliders)


_BAND_MAPPING = _build_band_mapping_section()

_GRAVITAS = SectionDef(
    title="Gravitas",
    sliders=[
        SliderDef("Push strength",       "gravitas_push_strength",         0.5, 10.0, 0.1,  "{:.1f}"),
        SliderDef("Swirl strength",      "gravitas_swirl_strength",        0.0, 6.0, 0.05, "{:.2f}"),
        SliderDef("Jitter strength",     "gravitas_jitter_strength",       0.0, 4.0, 0.05, "{:.2f}"),
        SliderDef("Transient boost",     "gravitas_transient_boost",       0.0, 5.0, 0.05, "{:.2f}"),
        SliderDef("Centroid influence",  "gravitas_centroid_influence",    0.0, 2.0, 0.02, "{:.2f}"),
        # Exponential mechanic
        SliderDef("Exp decay rate",      "gravitas_exponential_decay_rate", 0.05, 0.5, 0.005, "{:.3f}"),
        SliderDef("Exp initial speed",   "gravitas_exponential_initial_speed", 0.1, 3.0, 0.05, "{:.2f}"),
        # Spring mechanic
        SliderDef("Spring strength",     "gravitas_spring_strength",    0.1, 2.0, 0.02, "{:.2f}"),
        SliderDef("Spring damping",      "gravitas_spring_damping",     0.1, 1.0, 0.01, "{:.2f}"),
        SliderDef("Spring mass",         "gravitas_spring_mass",        0.1, 5.0, 0.05, "{:.2f}"),
        # Linear mechanic
        SliderDef("Linear return speed", "gravitas_linear_return_speed",    0.1, 1.0, 0.01, "{:.2f}"),
        SliderDef("Linear damping",      "gravitas_linear_damping_factor",  0.5, 1.0, 0.01, "{:.2f}"),
    ],
)

_TORUS = SectionDef(
    title="Torus Knot",
    sliders=[
        SliderDef("Knot μ",        "knot_mu",                1,    10,   1,    "{:.0f}"),
        SliderDef("Knot ν",        "knot_nu",                1,    10,   1,    "{:.0f}"),
        SliderDef("Base radius",   "base_radius",            0.5,  5.0,  0.05, "{:.2f}"),
        SliderDef("Tube radius",   "tube_radius",            0.1,  3.0,  0.05, "{:.2f}"),
        SliderDef("Rotation Y",    "base_rotation_speed_y",  0.0,  0.5,  0.005, "{:.3f}"),
        SliderDef("Rotation X",    "base_rotation_speed_x",  0.0,  0.5,  0.005, "{:.3f}"),
        SliderDef("Distortion",    "audio_distortion_scale", 0.0,  2.0,  0.05, "{:.2f}"),
        SliderDef("Rot boost",     "audio_rotation_boost",   0.0,  1.0,  0.01, "{:.2f}"),
    ],
)

_PENROSE = SectionDef(
    title="Penrose Triangle",
    sliders=[
        SliderDef("Triangle scale",  "penrose_triangle_scale",  100.0, 1000.0, 10.0, "{:.0f}"),
        SliderDef("Flow speed",      "penrose_flow_speed",        0.0,    2.0,  0.02, "{:.2f}"),
        SliderDef("Fold strength",   "penrose_fold_strength",     0.5,    5.0,  0.05, "{:.2f}"),
        SliderDef("Audio push",      "penrose_audio_push",        1.0,   10.0,  0.1,  "{:.1f}"),
        SliderDef("Particle spread", "penrose_particle_spread",  50.0,  500.0, 10.0, "{:.0f}"),
        SliderDef("Rotation speed",  "penrose_rotation_speed",    0.0,    1.0,  0.01, "{:.2f}"),
        SliderDef("Edge thickness",  "penrose_edge_thickness",   10.0,  100.0,  1.0,  "{:.0f}"),
    ],
)

_PLEXUS_SHAPE = SectionDef(
    title="Plexus shape",
    sliders=[
        SliderDef("Base radius",     "plexus_base_radius",            0.5, 4.0,  0.05, "{:.2f}"),
        SliderDef("Shell links",     "plexus_knn_links",               2,  16,   1,    "{:.0f}"),
        SliderDef("Chord ratio",     "plexus_chord_link_ratio",        0.0, 2.0,  0.02, "{:.2f}"),
        SliderDef("Crumple amount",  "plexus_crumple_amplitude",       0.0, 2.0,  0.02, "{:.2f}"),
        SliderDef("Crumple freq",    "plexus_crumple_frequency",       0.1, 5.0,  0.05, "{:.2f}"),
        SliderDef("Crumple octaves", "plexus_crumple_octaves",         1,   5,   1,    "{:.0f}"),
        SliderDef("Crumple evolve",  "plexus_crumple_evolve_speed",    0.0, 1.0,  0.01, "{:.2f}"),
        SliderDef("Tangential mix",  "plexus_crumple_tangential_mix",  0.0, 1.0,  0.02, "{:.2f}"),
    ],
)

_PLEXUS_EDGES = SectionDef(
    title="Plexus edges",
    sliders=[
        SliderDef("Link threshold",   "plexus_connection_distance_factor",        0.3, 4.0, 0.02, "{:.2f}"),
        SliderDef("Link audio boost", "plexus_connection_distance_audio_boost",   0.0, 4.0, 0.02, "{:.2f}"),
        SliderDef("Edge width",       "plexus_edge_width",                        0.5, 6.0, 0.1,  "{:.1f}"),
        SliderDef("Edge opacity",     "plexus_edge_base_alpha",                   0.0, 1.0, 0.01, "{:.2f}"),
        SliderDef("Length falloff",   "plexus_edge_length_falloff",               0.0, 2.0, 0.02, "{:.2f}"),
        SliderDef("Min brightness",   "plexus_min_brightness",                    0.0, 1.0, 0.01, "{:.2f}"),
        SliderDef("Node dot size",    "plexus_node_point_size",                   0.0, 6.0, 0.1,  "{:.1f}"),
        SliderDef("Node brightness",  "plexus_node_brightness_boost",             0.0, 1.0, 0.01, "{:.2f}"),
    ],
)

_PLEXUS_MOTION = SectionDef(
    title="Plexus motion",
    sliders=[
        SliderDef("Rotation Y",     "plexus_rotation_speed_y",   0.0,  0.5,  0.005, "{:.3f}"),
        SliderDef("Rotation X",     "plexus_rotation_speed_x",   0.0,  0.5,  0.005, "{:.3f}"),
        SliderDef("Rotation Z",     "plexus_rotation_speed_z",   0.0,  0.5,  0.005, "{:.3f}"),
        SliderDef("Precession",     "plexus_precession_wobble",  0.0,  1.0,  0.01,  "{:.2f}"),
        SliderDef("Breath speed",   "plexus_breath_speed",       0.0,  2.0,  0.02,  "{:.2f}"),
        SliderDef("Breath amount",  "plexus_breath_amplitude",   0.0,  0.5,  0.01,  "{:.2f}"),
    ],
)

_PLEXUS_AUDIO = SectionDef(
    title="Plexus audio reactivity",
    sliders=[
        SliderDef("Crumple boost",    "plexus_audio_crumple_boost",       0.0, 3.0, 0.02, "{:.2f}"),
        SliderDef("Rotation boost",   "plexus_audio_rotation_boost",      0.0, 2.0, 0.02, "{:.2f}"),
        SliderDef("Brightness boost", "plexus_audio_brightness_boost",    0.0, 2.0, 0.02, "{:.2f}"),
        SliderDef("Flash strength",   "plexus_transient_flash_strength",  0.0, 3.0, 0.02, "{:.2f}"),
        SliderDef("Flash decay",      "plexus_transient_flash_decay",     0.5, 0.99, 0.005, "{:.3f}"),
        SliderDef("Bass scale",       "plexus_bass_scale_influence",      0.0, 2.0, 0.02, "{:.2f}"),
        SliderDef("Mid swirl",        "plexus_mid_swirl_influence",       0.0, 2.0, 0.02, "{:.2f}"),
        SliderDef("Treble jitter",    "plexus_treble_jitter_influence",   0.0, 2.0, 0.02, "{:.2f}"),
    ],
)


# ── factory ────────────────────────────────────────────────────────────────────

def sections_for(style: str, mode: str | None) -> list[SectionDef]:
    """Return the correct SectionDef list for a given style/mode combination."""
    if style == "Torus Knot":
        return [_COMMON, _TORUS]
    elif style == "Penrose":
        return [_COMMON, _PENROSE]
    elif style == "Plexus":
        return [_COMMON, _PLEXUS_SHAPE, _PLEXUS_EDGES, _PLEXUS_MOTION, _PLEXUS_AUDIO]
    elif mode == "Impact":
        return [_COMMON, _CLOUD_MOTION, _CLOUD_AUDIO, _BAND_MAPPING]
    else:  # Gravitas (default)
        return [_COMMON, _CLOUD_MOTION, _CLOUD_AUDIO, _BAND_MAPPING, _GRAVITAS]


# ── per-mode canonical defaults ────────────────────────────────────────────────
# These mirror the -s / interactive flag defaults and are used by the Reset button.

_DEFAULTS_GRAVITAS: dict[str, object] = {
    "num_particles": 1023,
    "max_point_size": 5.72,
    "fade_alpha": 255,
    "brightness_gamma": 3.0,
    "audio_gain": 50.0,
    "audio_transient_sensitivity": 1.1,
    "cloud_density_sigma": 0.9,
    "cloud_drift_speed": 1.0,
    "cloud_breath_speed": 0.3,
    "cloud_rotation_speed_y": 0.08,
    "cloud_rotation_speed_x": 0.05,
    "audio_noise_threshold": 0.03,
    "cloud_audio_drift_boost": 0.3,
    "cloud_audio_breath_boost": 0.5,
    "cloud_audio_size_boost": 0.3,
    "gravitas_push_strength": 2.3,
    "gravitas_swirl_strength": 1.0,
    "gravitas_jitter_strength": 0.45,
    "gravitas_transient_boost": 0.55,
    "gravitas_centroid_influence": 0.35,
    "gravitas_return_mechanic": "spring",
    "gravitas_exponential_decay_rate": 0.15,
    "gravitas_exponential_initial_speed": 1.5,
    "gravitas_spring_strength": 2.0,
    "gravitas_spring_damping": 0.7,
    "gravitas_spring_mass": 0.7,
    "gravitas_linear_return_speed": 0.3,
    "gravitas_linear_damping_factor": 0.9,
    "band1_particle_count_scale": 1.0,
    "band2_particle_count_scale": 1.0,
    "band3_particle_count_scale": 1.0,
    "band4_particle_count_scale": 1.0,
    "band5_particle_count_scale": 1.0,
    "band6_particle_count_scale": 1.0,
    "band7_particle_count_scale": 1.0,
    "band8_particle_count_scale": 1.0,
    "band1_particle_size_scale": 1.0,
    "band2_particle_size_scale": 1.0,
    "band3_particle_size_scale": 1.0,
    "band4_particle_size_scale": 1.0,
    "band5_particle_size_scale": 1.0,
    "band6_particle_size_scale": 1.0,
    "band7_particle_size_scale": 1.0,
    "band8_particle_size_scale": 1.0,
}

_DEFAULTS_IMPACT: dict[str, object] = {
    "num_particles": 1023,
    "max_point_size": 5.72,
    "fade_alpha": 255,
    "brightness_gamma": 3.0,
    "audio_gain": 50.0,
    "audio_transient_sensitivity": 1.1,
    "cloud_density_sigma": 0.9,
    "cloud_drift_speed": 1.0,
    "cloud_breath_speed": 0.3,
    "cloud_rotation_speed_y": 0.08,
    "cloud_rotation_speed_x": 0.05,
    "audio_noise_threshold": 0.03,
    "cloud_audio_drift_boost": 0.3,
    "cloud_audio_breath_boost": 0.5,
    "cloud_audio_size_boost": 0.3,
    "band1_particle_count_scale": 1.0,
    "band2_particle_count_scale": 1.0,
    "band3_particle_count_scale": 1.0,
    "band4_particle_count_scale": 1.0,
    "band5_particle_count_scale": 1.0,
    "band6_particle_count_scale": 1.0,
    "band7_particle_count_scale": 1.0,
    "band8_particle_count_scale": 1.0,
    "band1_particle_size_scale": 1.0,
    "band2_particle_size_scale": 1.0,
    "band3_particle_size_scale": 1.0,
    "band4_particle_size_scale": 1.0,
    "band5_particle_size_scale": 1.0,
    "band6_particle_size_scale": 1.0,
    "band7_particle_size_scale": 1.0,
    "band8_particle_size_scale": 1.0,
}

_DEFAULTS_TORUS: dict[str, object] = {
    "num_particles": 1023,
    "max_point_size": 5.72,
    "fade_alpha": 255,
    "brightness_gamma": 3.0,
    "audio_gain": 50.0,
    "audio_transient_sensitivity": 1.1,
    "knot_mu": 2,
    "knot_nu": 3,
    "base_radius": 2.2,
    "tube_radius": 0.9,
    "base_rotation_speed_y": 0.25,
    "base_rotation_speed_x": 0.13,
    "audio_distortion_scale": 0.8,
    "audio_rotation_boost": 0.35,
}

_DEFAULTS_PENROSE: dict[str, object] = {
    "num_particles": 1023,
    "max_point_size": 5.72,
    "fade_alpha": 25,
    "brightness_gamma": 1.8,
    "audio_gain": 50.0,
    "audio_transient_sensitivity": 1.1,
    "penrose_triangle_scale": 400.0,
    "penrose_flow_speed": 0.5,
    "penrose_fold_strength": 2.0,
    "penrose_audio_push": 3.0,
    "penrose_particle_spread": 200.0,
    "penrose_rotation_speed": 0.3,
    "penrose_edge_thickness": 50.0,
}

_DEFAULTS_PLEXUS: dict[str, object] = {
    "num_particles": 1023,
    "max_point_size": 5.72,
    "fade_alpha": 25,
    "brightness_gamma": 1.8,
    "audio_gain": 50.0,
    "audio_transient_sensitivity": 1.1,
    "plexus_base_radius": 1.6,
    "plexus_knn_links": 5,
    "plexus_chord_link_ratio": 0.5,
    "plexus_connection_distance_factor": 0.9,
    "plexus_connection_distance_audio_boost": 1.8,
    "plexus_crumple_amplitude": 0.35,
    "plexus_crumple_frequency": 1.6,
    "plexus_crumple_octaves": 3,
    "plexus_crumple_evolve_speed": 0.06,
    "plexus_crumple_tangential_mix": 0.35,
    "plexus_rotation_speed_y": 0.06,
    "plexus_rotation_speed_x": 0.03,
    "plexus_rotation_speed_z": 0.012,
    "plexus_precession_wobble": 0.3,
    "plexus_breath_speed": 0.12,
    "plexus_breath_amplitude": 0.08,
    "plexus_edge_width": 1.4,
    "plexus_edge_base_alpha": 0.9,
    "plexus_edge_length_falloff": 0.5,
    "plexus_min_brightness": 0.45,
    "plexus_node_point_size": 0.0,
    "plexus_node_brightness_boost": 0.25,
    "plexus_audio_crumple_boost": 0.8,
    "plexus_audio_rotation_boost": 0.35,
    "plexus_audio_brightness_boost": 0.45,
    "plexus_transient_flash_strength": 0.9,
    "plexus_transient_flash_decay": 0.85,
    "plexus_bass_scale_influence": 0.3,
    "plexus_mid_swirl_influence": 0.4,
    "plexus_treble_jitter_influence": 0.35,
}


def defaults_for(style: str, mode: str | None) -> dict[str, object]:
    """Return the canonical default values for a given style/mode combination."""
    if style == "Torus Knot":
        return dict(_DEFAULTS_TORUS)
    elif style == "Penrose":
        return dict(_DEFAULTS_PENROSE)
    elif style == "Plexus":
        return dict(_DEFAULTS_PLEXUS)
    elif mode == "Impact":
        return dict(_DEFAULTS_IMPACT)
    else:
        return dict(_DEFAULTS_GRAVITAS)


def build_overlay(cfg: Config, style: str, mode: str | None) -> OverlayPanel:
    """Create an OverlayPanel with live style/mode selectors and parameter sliders.

    Args:
        cfg: Live Config object; sliders mutate it directly.
        style: The initial style string ("Particle Cloud", "Torus Knot", "Penrose").
        mode: The initial mode string ("Gravitas", "Impact") or None.

    Returns:
        A configured OverlayPanel ready to receive events and draw calls.

    """
    return OverlayPanel(cfg, sections_for, style, mode, defaults_for)


_PRESET_DIR = Path(".0folder.bak") / "presets"


def _preset_attrs(style: str, mode: str | None) -> list[str]:
    attrs: list[str] = []
    for sec in sections_for(style, mode):
        for sdef in sec.sliders:
            if sdef.attr not in attrs:
                attrs.append(sdef.attr)
    return attrs


def save_preset(cfg: Config, style: str, mode: str | None, name: str) -> Path:
    """Persist current panel values to JSON preset file."""
    preset_name = (name or "default").strip().replace(" ", "_")
    _PRESET_DIR.mkdir(parents=True, exist_ok=True)
    path = _PRESET_DIR / f"{preset_name}.json"

    attrs = _preset_attrs(style, mode)
    values = {attr: getattr(cfg, attr) for attr in attrs if hasattr(cfg, attr)}
    payload = {
        "name": preset_name,
        "style": style,
        "mode": mode,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "values": values,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_preset(cfg: Config, style: str, mode: str | None, name: str) -> dict[str, int]:
    """Load panel values from JSON preset file into cfg."""
    preset_name = (name or "default").strip().replace(" ", "_")
    path = _PRESET_DIR / f"{preset_name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    applied = 0
    skipped = 0
    allowed_attrs = set(_preset_attrs(style, mode))
    for attr, val in payload.get("values", {}).items():
        if attr in allowed_attrs and hasattr(cfg, attr):
            setattr(cfg, attr, val)
            applied += 1
        else:
            skipped += 1

    return {"applied": applied, "skipped": skipped}
