"""Interactive CLI configuration."""

from InquirerPy import inquirer

from particled.config import Config

# ========== Transformer Functions for Visual Dials ==========


def _particles_transformer(result: str) -> str:
    """Transform particle count to visual bar (100-20000 range)."""
    value = int(result or 5500)
    # Normalize to 0-100 range
    normalized = ((value - 100) * 100) // (20000 - 100)
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value}"


def _alpha_transformer(result: str) -> str:
    """Transform fade alpha to visual bar (0-255 range)."""
    value = int(result or 25)
    normalized = (value * 100) // 255
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value}"


def _gamma_transformer(result: str) -> str:
    """Transform brightness gamma to visual bar (0.5-3.0 range)."""
    value = float(result or 1.8)
    # Normalize to 0-100 range
    normalized = int(((value - 0.5) * 100) / (3.0 - 0.5))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _gain_transformer(result: str) -> str:
    """Transform audio gain to visual bar (0.0-200.0 range)."""
    value = float(result or 50.0)
    normalized = int((value * 100) / 200.0)
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.1f}"


def _density_transformer(result: str) -> str:
    """Transform density sigma to visual bar (0.1-5.0 range)."""
    value = float(result or 1.0)
    normalized = int(((value - 0.1) * 100) / (5.0 - 0.1))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _drift_transformer(result: str) -> str:
    """Transform drift speed to visual bar (0.0-1.0 range)."""
    value = float(result or 0.1)
    normalized = int((value * 100) / 1.0)
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _rotation_transformer(result: str) -> str:
    """Transform rotation speed to visual bar (0.0-0.5 range)."""
    value = float(result or 0.05)
    normalized = int((value * 100) / 0.5)
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.3f}"


def _breath_transformer(result: str) -> str:
    """Transform breath speed to visual bar (0.0-2.0 range)."""
    value = float(result or 0.3)
    normalized = int((value * 100) / 2.0)
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _threshold_transformer(result: str) -> str:
    """Transform audio threshold to visual bar (0.0-0.5 range)."""
    value = float(result or 0.02)
    normalized = int((value * 100) / 0.5)
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.3f}"


def _push_transformer(result: str) -> str:
    """Transform push strength to visual bar (0.5-10.0 range)."""
    value = float(result or 4.5)
    normalized = int(((value - 0.5) * 100) / (10.0 - 0.5))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.1f}"


def _spring_strength_transformer(result: str) -> str:
    """Transform spring strength to visual bar (0.1-2.0 range)."""
    value = float(result or 2.0)
    normalized = int(((value - 0.1) * 100) / (2.0 - 0.1))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _damping_transformer(result: str) -> str:
    """Transform damping to visual bar (0.1-1.0 range)."""
    value = float(result or 0.7)
    normalized = int(((value - 0.1) * 100) / (1.0 - 0.1))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _mass_transformer(result: str) -> str:
    """Transform spring mass to visual bar (0.1-5.0 range)."""
    value = float(result or 0.7)
    normalized = int(((value - 0.1) * 100) / (5.0 - 0.1))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _linear_speed_transformer(result: str) -> str:
    """Transform linear return speed to visual bar (0.1-1.0 range)."""
    value = float(result or 0.3)
    normalized = int(((value - 0.1) * 100) / (1.0 - 0.1))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _linear_damping_transformer(result: str) -> str:
    """Transform linear damping to visual bar (0.5-1.0 range)."""
    value = float(result or 0.9)
    normalized = int(((value - 0.5) * 100) / (1.0 - 0.5))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _decay_transformer(result: str) -> str:
    """Transform decay rate to visual bar (0.05-0.5 range)."""
    value = float(result or 0.15)
    normalized = int(((value - 0.05) * 100) / (0.5 - 0.05))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _knot_transformer(result: str) -> str:
    """Transform knot parameter to visual bar (1-10 range)."""
    value = int(result or 2)
    normalized = ((value - 1) * 100) // (10 - 1)
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value}"


def _triangle_scale_transformer(result: str) -> str:
    """Transform triangle scale to visual bar (100-1000 range)."""
    value = float(result or 400.0)
    normalized = int(((value - 100) * 100) / (1000 - 100))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.1f}"


def _flow_speed_transformer(result: str) -> str:
    """Transform flow speed to visual bar (0.0-2.0 range)."""
    value = float(result or 0.5)
    normalized = int((value * 100) / 2.0)
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _fold_strength_transformer(result: str) -> str:
    """Transform fold strength to visual bar (0.5-5.0 range)."""
    value = float(result or 2.0)
    normalized = int(((value - 0.5) * 100) / (5.0 - 0.5))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


def _audio_push_transformer(result: str) -> str:
    """Transform audio push to visual bar (1.0-10.0 range)."""
    value = float(result or 3.0)
    normalized = int(((value - 1.0) * 100) / (10.0 - 1.0))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.1f}"


def _particle_spread_transformer(result: str) -> str:
    """Transform particle spread to visual bar (50-500 range)."""
    value = float(result or 200.0)
    normalized = int(((value - 50) * 100) / (500 - 50))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.1f}"


def _edge_thickness_transformer(result: str) -> str:
    """Transform edge thickness to visual bar (10-100 range)."""
    value = float(result or 50.0)
    normalized = int(((value - 10) * 100) / (100 - 10))
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.1f}"


def _penrose_rotation_transformer(result: str) -> str:
    """Transform Penrose rotation speed to visual bar (0.0-1.0 range)."""
    value = float(result or 0.3)
    normalized = int((value * 100) / 1.0)
    steps = 15
    filled = max(0, min(steps, normalized * steps // 100))
    bar = "█" * filled + "░" * (steps - filled)
    return f"[{bar}] {value:.2f}"


# ========== Common Input Helpers ==========


def _prompt_num_particles(default: int = 5500) -> int:
    """Prompt for number of particles.

    Args:
        default: Default value for number of particles.

    Returns:
        Number of particles as integer.

    """
    return int(
        inquirer.number(
            message="Number of particles:",
            default=default,
            min_allowed=100,
            max_allowed=20000,
            transformer=_particles_transformer,
        ).execute()
    )


def _prompt_fade_alpha(default: int = 25) -> int:
    """Prompt for trail fade alpha.

    Args:
        default: Default value for fade alpha.

    Returns:
        Fade alpha value as integer.

    """
    return int(
        inquirer.number(
            message="Trail fade alpha (0=long trails, 255=no trails):",
            default=default,
            min_allowed=0,
            max_allowed=255,
            transformer=_alpha_transformer,
        ).execute()
    )


def _prompt_brightness_gamma(default: float = 3.0) -> float:
    """Prompt for brightness gamma.

    Args:
        default: Default value for brightness gamma.

    Returns:
        Brightness gamma value as float.

    """
    return float(
        inquirer.number(
            message="Brightness gamma (contrast):",
            default=default,
            min_allowed=0.5,
            max_allowed=3.0,
            float_allowed=True,
            transformer=_gamma_transformer,
        ).execute()
    )


def _prompt_audio_gain(default: float = 50.0) -> float:
    """Prompt for audio reactivity gain.

    Args:
        default: Default value for audio gain.

    Returns:
        Audio gain value as float.

    """
    return float(
        inquirer.number(
            message="Audio reactivity gain:",
            default=default,
            min_allowed=0.0,
            max_allowed=200.0,
            float_allowed=True,
            transformer=_gain_transformer,
        ).execute()
    )


def _prompt_density_sigma(default: float = 0.9) -> float:
    """Prompt for density sigma (Particle Cloud modes).

    Args:
        default: Default value for density sigma.

    Returns:
        Density sigma value as float.

    """
    return float(
        inquirer.number(
            message="Density sigma (lower=denser center):",
            default=default,
            min_allowed=0.01,
            max_allowed=5.0,
            float_allowed=True,
            transformer=_density_transformer,
        ).execute()
    )


def _prompt_drift_speed(default: float = 0.1) -> float:
    """Prompt for drift speed (Particle Cloud modes).

    Args:
        default: Default value for drift speed.

    Returns:
        Drift speed value as float.

    """
    return float(
        inquirer.number(
            message="Drift speed:",
            default=default,
            min_allowed=0.0,
            max_allowed=1.0,
            float_allowed=True,
            transformer=_drift_transformer,
        ).execute()
    )


def _prompt_rotation_speeds(
    default_y: float = 0.05, default_x: float = 0.03
) -> tuple[float, float]:
    """Prompt for rotation speeds around Y and X axes.

    Args:
        default_y: Default Y-axis rotation speed.
        default_x: Default X-axis rotation speed.

    Returns:
        Tuple of (rotation_speed_y, rotation_speed_x) as floats.

    """
    rotation_y = float(
        inquirer.number(
            message="Rotation speed (Y-axis):",
            default=default_y,
            min_allowed=0.0,
            max_allowed=0.5,
            float_allowed=True,
            transformer=_rotation_transformer,
        ).execute()
    )

    rotation_x = float(
        inquirer.number(
            message="Rotation speed (X-axis):",
            default=default_x,
            min_allowed=0.0,
            max_allowed=0.5,
            float_allowed=True,
            transformer=_rotation_transformer,
        ).execute()
    )

    return rotation_y, rotation_x


# ========== Style and Mode Selection ==========


def get_visualization_style() -> str:
    """Prompt user to select visualization style.

    Returns:
        Selected visualization style name.

    """
    return inquirer.select(
        message="Select visualization style:",
        choices=["Particle Cloud", "Torus Knot", "Penrose"],
        default="Particle Cloud",
    ).execute()


def choose_display() -> int:
    """Interactively select which monitor to use for fullscreen.

    Queries GLFW for available monitors and presents them as a numbered
    list.  Returns the GLFW monitor index (0-based) for the chosen monitor.

    Returns:
        GLFW monitor index of the selected monitor.

    """
    import glfw
    if not glfw.init():
        return 0
    monitors = glfw.get_monitors()
    n = len(monitors)
    choices = []
    for i, m in enumerate(monitors):
        vm = glfw.get_video_mode(m)
        if vm is not None:
            w, h = vm.size.width, vm.size.height
            # get_video_mode() returns raw scan-out dims; on compositor-rotated
            # portrait displays those are swapped vs the actual framebuffer.
            # Show both so the user can identify the display, but skip the
            # orientation label since it may be misleading.
            choices.append({"name": f"Display {i + 1}  {w}×{h}", "value": i})
        else:
            choices.append({"name": f"Display {i + 1}", "value": i})
    # Don't terminate GLFW here — main() will re-use the existing init.

    if n == 1:
        return 0  # nothing to choose

    return inquirer.select(
        message="Select display for fullscreen:",
        choices=choices,
    ).execute()


def get_particle_cloud_mode() -> str:
    """Prompt user to select Particle Cloud sub-mode.

    Returns:
        Selected Particle Cloud mode ('Gravitas' or 'Impact').

    """
    return inquirer.select(
        message="Select Particle Cloud mode:",
        choices=["Gravitas", "Impact"],
        default="Gravitas",
    ).execute()


def configure_impact() -> Config:
    """Prompt user for Particle Cloud Impact mode configuration.

    Returns:
        Configured Config object for Impact mode.

    """
    print("\n💥  Particle Cloud - Impact Mode Configuration\n")

    density_sigma = _prompt_density_sigma(default=0.9)
    drift_speed = _prompt_drift_speed(default=1.0)

    breath_speed = float(
        inquirer.number(
            message="Breathing speed:",
            default=0.3,
            min_allowed=0.0,
            max_allowed=2.0,
            float_allowed=True,
            transformer=_breath_transformer,
        ).execute()
    )

    rotation_speed_y, rotation_speed_x = _prompt_rotation_speeds(
        default_y=0.08, default_x=0.05
    )
    audio_gain = _prompt_audio_gain(default=50.0)
    fade_alpha = _prompt_fade_alpha(default=255)
    brightness_gamma = _prompt_brightness_gamma(default=3.0)

    cfg = Config()
    cfg.cloud_density_sigma = density_sigma
    cfg.cloud_drift_speed = drift_speed
    cfg.cloud_breath_speed = breath_speed
    cfg.cloud_rotation_speed_y = rotation_speed_y
    cfg.cloud_rotation_speed_x = rotation_speed_x
    cfg.audio_gain = audio_gain
    cfg.fade_alpha = fade_alpha
    cfg.brightness_gamma = brightness_gamma

    return cfg


def _configure_gravitas_return_mechanic() -> tuple[str, dict]:
    """Prompt for Gravitas return mechanic and parameters.

    Returns:
        Tuple of (mechanic_name, parameters_dict).

    """
    mechanic = inquirer.select(
        message="Return mechanic:",
        choices=["exponential", "spring", "linear"],
        default="spring",
    ).execute()

    params = {}
    if mechanic == "spring":
        params["spring_strength"] = inquirer.number(
            message="Spring strength:",
            default=2.0,
            min_allowed=0.1,
            max_allowed=2.0,
            float_allowed=True,
            transformer=_spring_strength_transformer,
        ).execute()

        params["spring_damping"] = inquirer.number(
            message="Spring damping:",
            default=0.7,
            min_allowed=0.1,
            max_allowed=1.0,
            float_allowed=True,
            transformer=_damping_transformer,
        ).execute()

        params["spring_mass"] = inquirer.number(
            message="Spring mass:",
            default=0.7,
            min_allowed=0.1,
            max_allowed=5.0,
            float_allowed=True,
            transformer=_mass_transformer,
        ).execute()
    elif mechanic == "linear":
        params["linear_return_speed"] = inquirer.number(
            message="Linear return speed:",
            default=0.3,
            min_allowed=0.1,
            max_allowed=1.0,
            float_allowed=True,
            transformer=_linear_speed_transformer,
        ).execute()

        params["linear_damping"] = inquirer.number(
            message="Linear damping factor:",
            default=0.9,
            min_allowed=0.5,
            max_allowed=1.0,
            float_allowed=True,
            transformer=_linear_damping_transformer,
        ).execute()
    else:  # exponential
        params["decay_rate"] = inquirer.number(
            message="Exponential decay rate:",
            default=0.15,
            min_allowed=0.05,
            max_allowed=0.5,
            float_allowed=True,
            transformer=_decay_transformer,
        ).execute()

    return mechanic, params


def configure_gravitas() -> Config:
    """Prompt user for Particle Cloud Gravitas mode configuration.

    Returns:
        Configured Config object for Gravitas mode.

    """
    print("\n⚛️  Particle Cloud - Gravitas Mode Configuration\n")

    density_sigma = _prompt_density_sigma(default=0.9)
    drift_speed = _prompt_drift_speed(default=1.0)
    rotation_speed_y, rotation_speed_x = _prompt_rotation_speeds(
        default_y=0.08, default_x=0.05
    )

    audio_noise_threshold = float(
        inquirer.number(
            message="Audio noise threshold (ignore below this level):",
            default=0.02,
            min_allowed=0.0,
            max_allowed=0.5,
            float_allowed=True,
            transformer=_threshold_transformer,
        ).execute()
    )

    push_strength = float(
        inquirer.number(
            message="Audio push strength:",
            default=3.5,
            min_allowed=0.5,
            max_allowed=10.0,
            float_allowed=True,
            transformer=_push_transformer,
        ).execute()
    )

    return_mechanic, mechanic_params = _configure_gravitas_return_mechanic()

    fade_alpha = _prompt_fade_alpha(default=255)
    brightness_gamma = _prompt_brightness_gamma(default=3.0)

    cfg = Config()
    cfg.cloud_density_sigma = density_sigma
    cfg.cloud_drift_speed = drift_speed
    cfg.cloud_rotation_speed_y = rotation_speed_y
    cfg.cloud_rotation_speed_x = rotation_speed_x
    cfg.audio_noise_threshold = audio_noise_threshold
    cfg.gravitas_push_strength = push_strength
    cfg.gravitas_return_mechanic = return_mechanic

    if return_mechanic == "spring":
        cfg.gravitas_spring_strength = float(mechanic_params["spring_strength"])
        cfg.gravitas_spring_damping = float(mechanic_params["spring_damping"])
        cfg.gravitas_spring_mass = float(mechanic_params["spring_mass"])
    elif return_mechanic == "linear":
        cfg.gravitas_linear_return_speed = float(mechanic_params["linear_return_speed"])
        cfg.gravitas_linear_damping_factor = float(mechanic_params["linear_damping"])
    else:
        cfg.gravitas_exponential_decay_rate = float(mechanic_params["decay_rate"])

    cfg.fade_alpha = fade_alpha
    cfg.brightness_gamma = brightness_gamma

    return cfg


def configure_torus_knot() -> Config:
    """Prompt user for Torus Knot configuration.

    Returns:
        Configured Config object for Torus Knot.

    """
    print("\n🌀 Torus Knot Configuration\n")

    knot_mu = int(
        inquirer.number(
            message="Torus knot parameter μ (complexity):",
            default=2,
            min_allowed=1,
            max_allowed=10,
            transformer=_knot_transformer,
        ).execute()
    )

    knot_nu = int(
        inquirer.number(
            message="Torus knot parameter nu (complexity):",
            default=3,
            min_allowed=1,
            max_allowed=10,
            transformer=_knot_transformer,
        ).execute()
    )

    rotation_speed_y, rotation_speed_x = _prompt_rotation_speeds(
        default_y=0.25, default_x=0.13
    )
    audio_gain = _prompt_audio_gain(default=50.0)
    fade_alpha = _prompt_fade_alpha(default=255)
    brightness_gamma = _prompt_brightness_gamma(default=3.0)

    cfg = Config()
    cfg.knot_mu = knot_mu
    cfg.knot_nu = knot_nu
    cfg.base_rotation_speed_y = rotation_speed_y
    cfg.base_rotation_speed_x = rotation_speed_x
    cfg.audio_gain = audio_gain
    cfg.fade_alpha = fade_alpha
    cfg.brightness_gamma = brightness_gamma

    return cfg


def configure_penrose() -> Config:
    """Prompt user for Penrose Triangle configuration.

    Returns:
        Configured Config object for Penrose Triangle.

    """
    print("\n🔺 Penrose Triangle Configuration\n")

    triangle_scale = float(
        inquirer.number(
            message="Triangle scale (size in 3D space):",
            default=400.0,
            min_allowed=100.0,
            max_allowed=1000.0,
            float_allowed=True,
            transformer=_triangle_scale_transformer,
        ).execute()
    )

    flow_speed = float(
        inquirer.number(
            message="Particle flow speed:",
            default=0.5,
            min_allowed=0.0,
            max_allowed=2.0,
            float_allowed=True,
            transformer=_flow_speed_transformer,
        ).execute()
    )

    fold_strength = float(
        inquirer.number(
            message="Fold-back intensity:",
            default=2.0,
            min_allowed=0.5,
            max_allowed=5.0,
            float_allowed=True,
            transformer=_fold_strength_transformer,
        ).execute()
    )

    audio_push = float(
        inquirer.number(
            message="Audio-triggered push force:",
            default=3.0,
            min_allowed=1.0,
            max_allowed=10.0,
            float_allowed=True,
            transformer=_audio_push_transformer,
        ).execute()
    )

    particle_spread = float(
        inquirer.number(
            message="Particle spread when flowing out:",
            default=200.0,
            min_allowed=50.0,
            max_allowed=500.0,
            float_allowed=True,
            transformer=_particle_spread_transformer,
        ).execute()
    )

    rotation_speed = float(
        inquirer.number(
            message="Triangle rotation speed:",
            default=0.3,
            min_allowed=0.0,
            max_allowed=1.0,
            float_allowed=True,
            transformer=_penrose_rotation_transformer,
        ).execute()
    )

    edge_thickness = float(
        inquirer.number(
            message="Edge beam thickness:",
            default=50.0,
            min_allowed=10.0,
            max_allowed=100.0,
            float_allowed=True,
            transformer=_edge_thickness_transformer,
        ).execute()
    )

    audio_gain = _prompt_audio_gain(default=50.0)
    fade_alpha = _prompt_fade_alpha(default=25)
    brightness_gamma = _prompt_brightness_gamma(default=1.8)

    cfg = Config()
    cfg.penrose_triangle_scale = triangle_scale
    cfg.penrose_flow_speed = flow_speed
    cfg.penrose_fold_strength = fold_strength
    cfg.penrose_audio_push = audio_push
    cfg.penrose_particle_spread = particle_spread
    cfg.penrose_rotation_speed = rotation_speed
    cfg.penrose_edge_thickness = edge_thickness
    cfg.audio_gain = audio_gain
    cfg.fade_alpha = fade_alpha
    cfg.brightness_gamma = brightness_gamma

    return cfg


def configure_interactively(style: str) -> tuple[Config, str | None]:
    """Prompt user for style-specific configuration.

    Args:
        style: Selected visualization style name.

    Returns:
        Tuple of (default Config object, sub-mode name or None).

    """
    if style == "Particle Cloud":
        mode = get_particle_cloud_mode()
        return Config(), mode
    elif style == "Penrose":
        return Config(), None
    else:
        return Config(), None


def prompt_for_interactive_config() -> bool:
    """Ask user if they want interactive configuration.

    Returns:
        True if user wants interactive configuration, False otherwise.

    """
    return inquirer.confirm(
        message="Configure visualization parameters interactively?",
        default=True,
    ).execute()
