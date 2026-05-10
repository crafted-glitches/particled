"""Configuration settings for the particle visualizer."""

from dataclasses import dataclass


@dataclass
class Config:
    """Configuration dataclass for audio-reactive particle visualizer.

    This class holds all configuration parameters for the visualization system,
    including window settings, particle behavior, audio reactivity, and
    style-specific parameters for different visualization modes.

    The configuration uses sensible defaults that work well for most use cases,
    but all parameters can be customized either programmatically or through
    the interactive CLI configuration system.

    Attributes:
        Window Configuration:
            width: Window width in pixels. Default 900.
            height: Window height in pixels. Default 1600.
            fullscreen: Whether to run in fullscreen mode. Default False.
            fps: Target frames per second for rendering. Default 60.

        Particle Geometry:
            num_particles: Number of particles to render (100-20000). Default 5500.
            base_radius: Base radius for torus knot geometry. Default 2.2.
            tube_radius: Tube radius for torus knot structure. Default 0.9.
            knot_mu: Torus knot parameter μ (longitudinal loops). Default 2.
            knot_nu: Torus knot parameter ν (meridional loops). Default 3.
            z_offset: Z-axis offset for 3D projection. Default 7.0.
            pixel_scale: Scaling factor for screen projection. Default 220.0.
            fov: Field of view for perspective projection. Default 6.0.

        Motion & Rotation:
            base_rotation_speed_y: Base Y-axis rotation speed. Default 0.25.
            base_rotation_speed_x: Base X-axis rotation speed. Default 0.13.
            distortion_freq: Frequency of distortion oscillations. Default 5.0.
            distortion_speed: Speed of distortion animation. Default 0.5.

        Audio Reactivity:
            audio_gain: Microphone input amplification (0-200). Default 50.0.
            audio_radius_scale: Audio influence on radius (0-1). Default 0.65.
            audio_distortion_scale: Audio influence on distortion (0-2). Default 0.8.
            audio_rotation_boost: Audio influence on rotation (0-1). Default 0.35.

        Visual Style:
            bg_color: Background color as RGB tuple. Default (0, 0, 0).
            particle_color: Particle color as RGB tuple. Default (255, 255, 255).
            min_point_size: Minimum particle size in pixels. Default 1.
            max_point_size: Maximum particle size in pixels. Default 4.
            fade_alpha: Trail fade alpha (0=long trails, 255=none). Default 25.
            brightness_gamma: Gamma correction for brightness (0.5-3). Default 1.8.

        Audio Input:
            sample_rate: Audio sample rate in Hz. Default 44100.
            channels: Number of audio channels (1=mono). Default 1.
            blocksize: Audio buffer size in frames. Default 1024.

        Particle Cloud Specific:
            cloud_density_sigma: Gaussian distribution spread (0.1-5). Default 1.0.
            cloud_drift_speed: Drift animation speed (0-1). Default 0.1.
            cloud_breath_speed: Breathing animation speed (0-2). Default 0.3.
            cloud_drift_amplitude: Drift movement amplitude. Default 0.2.
            cloud_breath_amplitude: Breathing expansion amplitude. Default 0.15.
            cloud_rotation_speed_y: Y-axis rotation speed (0-0.5). Default 0.05.
            cloud_rotation_speed_x: X-axis rotation speed (0-0.5). Default 0.03.
            cloud_audio_drift_boost: Audio influence on drift (0-1). Default 0.3.
            cloud_audio_breath_boost: Audio influence on breathing (0-1). Default 0.5.
            cloud_audio_size_boost: Audio influence on particle size (0-1). Default 0.3.
            cloud_density_falloff: Density-based size falloff rate. Default 0.5.

        Penrose Triangle Specific:
            penrose_triangle_scale: Triangle size in 3D space (100-1000).
                Default 400.0.
            penrose_flow_speed: Particle flow animation speed (0-2).
                Default 0.5.
            penrose_fold_strength: Fold-back intensity when returning (0.5-5).
                Default 2.0.
            penrose_audio_push: Audio-triggered push force (1-10). Default 3.0.
            penrose_particle_spread: Spread distance when flowing out (50-500).
                Default 200.0.
            penrose_rotation_speed: Triangle rotation speed (0-1). Default 0.3.
            penrose_edge_thickness: Edge beam thickness in pixels (10-100).
                Default 50.0.

    Example:
        >>> # Use default configuration
        >>> config = Config()
        >>>
        >>> # Customize specific parameters
        >>> config = Config(
        ...     num_particles=10000,
        ...     audio_gain=75.0,
        ...     fps=120
        ... )
        >>>
        >>> # Modify after creation
        >>> config.cloud_density_sigma = 1.5
        >>> config.fade_alpha = 50

    """  # noqa: RUF002

    # ---------- Window ----------
    width: int = 900  # change to your screen size
    height: int = 1600
    fullscreen: bool = False
    fps: int = 60
    use_gl: bool = False  # True = GPU rendering via ModernGL (Quadro M1000M)

    # ---------- Particles / geometry ----------
    num_particles: int = 7500
    base_radius: float = 2.2
    tube_radius: float = 0.9
    knot_mu: int = 2  # torus-knot parameters
    knot_nu: int = 3
    z_offset: float = 7.0
    pixel_scale: float = 220.0
    fov: float = 6.0

    # ---------- Motion ----------
    base_rotation_speed_y: float = 0.25
    base_rotation_speed_x: float = 0.13
    distortion_freq: float = 5.0
    distortion_speed: float = 0.5

    # ---------- Audio reactivity ----------
    audio_gain: float = 50.0  # higher = more reactive
    audio_radius_scale: float = 0.65
    audio_distortion_scale: float = 0.8
    audio_rotation_boost: float = 0.35
    audio_noise_threshold: float = 0.02  # Baseline noise level to ignore (0-1)

    # ---------- Visual style ----------
    bg_color: tuple = (0, 0, 0)
    particle_color: tuple = (255, 255, 255)
    min_point_size: int = 1
    max_point_size: int = 4
    fade_alpha: int = 255  # 0=no trails, 255=instant clear
    brightness_gamma: float = 3.0

    # ---------- Audio input ----------
    sample_rate: int = 44100
    channels: int = 1
    blocksize: int = 1024

    # ---------- Particle Cloud specific ----------
    cloud_density_sigma: float = 0.9  # Gaussian spread (lower=denser center)
    cloud_drift_speed: float = 1.0  # Particle drift speed
    cloud_breath_speed: float = 0.3  # Breathing animation speed
    cloud_drift_amplitude: float = 0.2  # Drift movement amplitude
    cloud_breath_amplitude: float = 0.15  # Breathing expansion amplitude
    cloud_rotation_speed_y: float = 0.08  # Y-axis rotation speed
    cloud_rotation_speed_x: float = 0.05  # X-axis rotation speed
    cloud_audio_drift_boost: float = 0.3  # Audio influence on drift
    cloud_audio_breath_boost: float = 0.5  # Audio influence on breathing
    cloud_audio_size_boost: float = 0.3  # Audio influence on particle size
    cloud_density_falloff: float = 0.5  # Density-based size falloff rate

    # ---------- Gravitas mode specific ----------
    gravitas_push_strength: float = 3.5  # Outward push force from audio (0-5)
    gravitas_return_mechanic: str = "spring"  # spring, linear, exponential
    # Spring mechanic parameters
    gravitas_spring_strength: float = 2.0  # Spring force (0-2)
    gravitas_spring_damping: float = 0.7  # Spring damping (0-1)
    gravitas_spring_mass: float = 0.7  # Particle mass for spring (0.5-2)
    # Linear mechanic parameters
    gravitas_linear_return_speed: float = 0.3  # Return speed (0-1)
    gravitas_linear_damping_factor: float = 0.9  # Damping factor (0-1)
    # Exponential mechanic parameters
    gravitas_exponential_decay_rate: float = 0.15  # Decay rate (0-1)
    gravitas_exponential_initial_speed: float = 1.5  # Initial return speed (0-3)
    # Frequency band mapping
    gravitas_bass_range: tuple = (0.0, 0.3)  # Particle radius range for bass
    gravitas_mid_range: tuple = (0.3, 0.7)  # Particle radius range for mids
    gravitas_treble_range: tuple = (0.7, 1.0)  # Particle radius range for treble

    # ---------- Penrose Triangle specific ----------
    penrose_triangle_scale: float = 400.0  # Triangle size in 3D space (100-1000)
    penrose_flow_speed: float = 0.5  # Particle flow speed (0.0-2.0)
    penrose_fold_strength: float = 2.0  # Fold-back intensity (0.5-5.0)
    penrose_audio_push: float = 3.0  # Audio-triggered push force (1.0-10.0)
    penrose_particle_spread: float = 200.0  # Spread when flowing out (50-500)
    penrose_rotation_speed: float = 0.3  # Triangle rotation speed (0.0-1.0)
    penrose_edge_thickness: float = 50.0  # Edge beam thickness (10-100)
