"""Per-style overlay panel definitions.

Maps every CLI-configurable parameter to a SliderDef for each style/mode,
then assembles them into an OverlayPanel ready to attach to main.py.
"""

from __future__ import annotations

from particled.config import Config
from particled.visuals.overlay import OverlayPanel, SectionDef, SliderDef

# ── shared sections ────────────────────────────────────────────────────────────

_COMMON = SectionDef(
    title="Common",
    sliders=[
        SliderDef("Particles",        "num_particles",    100,   5000,  50,   "{:.0f}"),
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


# ── factory ────────────────────────────────────────────────────────────────────

def sections_for(style: str, mode: str | None) -> list[SectionDef]:
    """Return the correct SectionDef list for a given style/mode combination."""
    if style == "Torus Knot":
        return [_COMMON, _TORUS]
    elif style == "Penrose":
        return [_COMMON, _PENROSE]
    elif mode == "Impact":
        return [_COMMON, _CLOUD_MOTION, _CLOUD_AUDIO]
    else:  # Gravitas (default)
        return [_COMMON, _CLOUD_MOTION, _CLOUD_AUDIO, _GRAVITAS]


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


def defaults_for(style: str, mode: str | None) -> dict[str, object]:
    """Return the canonical default values for a given style/mode combination."""
    if style == "Torus Knot":
        return dict(_DEFAULTS_TORUS)
    elif style == "Penrose":
        return dict(_DEFAULTS_PENROSE)
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
