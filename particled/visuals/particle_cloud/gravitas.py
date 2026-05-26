"""Particle Cloud Gravitas mode - gravity-centered reactive expansion.

This module implements the Gravitas sub-mode of Particle Cloud, featuring
gravity-centered behavior where audio pushes particles outward from the center,
and they return to their original positions using configurable mechanics.
"""

import numpy as np

from particled.config import Config
from particled.visuals.particle_cloud.base import ParticleCloudBase


class ParticleCloudGravitas(ParticleCloudBase):
    """Gravity-centered particle cloud with reactive expansion and return.

    This visualization creates a particle cloud where audio impacts push particles
    outward from the center, and they slowly return to their base positions using
    spring, linear, or exponential mechanics. Different particles respond to
    different frequency bands (bass, mid, treble) for varied, organic movement.

    Visual characteristics:
    - Pure white particles on black background
    - Gaussian density falloff from center
    - Audio pushes particles radially outward
    - Configurable return-to-center mechanics
    - Frequency-band particle mapping
    - Gentle drift and rotation when idle

    Attributes:
        cfg: Configuration object with all parameters.
        base_x, base_y, base_z: Base particle positions in 3D space.
        phase_x, phase_y, phase_z: Random phase offsets for drift motion.
        density: Precalculated density weights for size variation.
        displacement_x, displacement_y, displacement_z: Current displacement from base.
        velocity_x, velocity_y, velocity_z: Current velocity for spring mechanics.
        radial_distance: Distance of each particle from origin (for freq mapping).

    """

    def __init__(self, cfg: Config):
        """Initialize the Gravitas particle cloud.

        Args:
            cfg: Configuration object containing visualization parameters.

        """
        super().__init__(cfg)
        self._last_draw_t: float | None = None
        self._swirl_env: float = 0.0
        self._jitter_env: float = 0.0
        self._initialize_particles()

    def _initialize_particles(self):
        """Initialize particles with displacement tracking for Gravitas mode."""
        # Initialize base particles (positions, phases, density)
        self._initialize_base_particles()

        cfg = self.cfg
        n = cfg.num_particles

        # Displacement and velocity tracking (for audio-driven movement)
        self.displacement_x = np.zeros(n)
        self.displacement_y = np.zeros(n)
        self.displacement_z = np.zeros(n)
        self.velocity_x = np.zeros(n)
        self.velocity_y = np.zeros(n)
        self.velocity_z = np.zeros(n)

        # Precompute frequency-band masks — radial_distance never changes after init
        self._bass_mask = (
            (self.radial_distance >= cfg.gravitas_bass_range[0])
            & (self.radial_distance <= cfg.gravitas_bass_range[1])
        )
        self._mid_mask = (
            (self.radial_distance >= cfg.gravitas_mid_range[0])
            & (self.radial_distance <= cfg.gravitas_mid_range[1])
        )
        self._treble_mask = (
            (self.radial_distance >= cfg.gravitas_treble_range[0])
            & (self.radial_distance <= cfg.gravitas_treble_range[1])
        )

    def _apply_audio_push(
        self,
        band_levels: tuple[float, float, float],
        dt: float = 1 / 60,
        audio_features: dict | None = None,
        t: float = 0.0,
    ):
        """Apply outward push force driven by real per-frequency-band levels.

        Voice frequency zones map to radial layers of the cloud:
          - Inner core  (bass_mask)   → chest resonance / voice fundamental ~80–300 Hz
          - Middle ring (mid_mask)    → vowel formants / speech clarity  ~300–3000 Hz
          - Outer shell (treble_mask) → sibilance / fricatives            ~3000–8000 Hz

        Args:
            band_levels: (bass, mid, treble) RMS levels from AudioMeter.get_band_levels().
            dt: Time delta for physics integration.

        """
        cfg = self.cfg

        bass_v, mid_v, treble_v = band_levels

        eff_bass   = max(0.0, bass_v   - cfg.audio_noise_threshold)
        eff_mid    = max(0.0, mid_v    - cfg.audio_noise_threshold)
        eff_treble = max(0.0, treble_v - cfg.audio_noise_threshold)

        multibands = None
        transient = 0.0
        centroid = 0.0
        if audio_features is not None:
            mb = audio_features.get("bands")
            if mb is not None:
                multibands = np.asarray(mb, dtype=np.float32)
            transient = float(audio_features.get("transient", 0.0))
            centroid = float(audio_features.get("centroid", 0.0))

        # Use log-spaced multiband response when available; otherwise preserve
        # the original 3-zone mapping.
        if multibands is not None and len(multibands) >= 3:
            n = len(multibands)
            idx = np.clip((self.radial_distance * (n - 1)).astype(np.int32), 0, n - 1)
            freq_response = multibands[idx]
        else:
            freq_response = np.zeros_like(self.radial_distance)
            freq_response[self._bass_mask] = eff_bass
            freq_response[self._mid_mask] = eff_mid
            freq_response[self._treble_mask] = eff_treble

        freq_response = np.maximum(0.0, freq_response - cfg.audio_noise_threshold)
        # Preserve multiband detail while reducing abrupt force spikes.
        freq_response = np.tanh(freq_response * 1.1)

        # Higher spectral centroid biases push toward the cloud exterior.
        outer_bias = 1.0 + cfg.gravitas_centroid_influence * centroid * self.radial_distance
        push_strength = cfg.gravitas_push_strength * freq_response * outer_bias

        # Normalize base positions to get radial direction
        base_magnitude = np.sqrt(
            self.base_x**2 + self.base_y**2 + self.base_z**2 + 1e-8
        )
        dir_x = self.base_x / base_magnitude
        dir_y = self.base_y / base_magnitude
        dir_z = self.base_z / base_magnitude

        # Apply push to displacement
        self.displacement_x += dir_x * push_strength * dt
        self.displacement_y += dir_y * push_strength * dt
        self.displacement_z += dir_z * push_strength * dt

        # Mid energy drives a tangential swirl around the center.
        swirl_drive = eff_mid
        if multibands is not None and len(multibands) >= 3:
            l = max(1, len(multibands) // 3)
            h = max(l + 1, (2 * len(multibands)) // 3)
            swirl_drive = float(np.mean(multibands[l:h]))
        tang_norm = np.sqrt(self.base_x**2 + self.base_y**2 + 1e-8)
        tan_x = -self.base_y / tang_norm
        tan_y = self.base_x / tang_norm
        swirl_target = max(0.0, swirl_drive - cfg.audio_noise_threshold)
        self._swirl_env = 0.86 * self._swirl_env + 0.14 * swirl_target
        swirl_strength = cfg.gravitas_swirl_strength * self._swirl_env
        self.displacement_x += tan_x * swirl_strength * dt
        self.displacement_y += tan_y * swirl_strength * dt

        # Treble + transients create controlled micro-jitter for crisp attacks.
        treble_drive = eff_treble
        if multibands is not None and len(multibands) >= 3:
            treble_drive = float(np.mean(multibands[(2 * len(multibands)) // 3:]))
        jitter_target = max(0.0, treble_drive - cfg.audio_noise_threshold)
        jitter_target += cfg.gravitas_transient_boost * transient
        self._jitter_env = 0.90 * self._jitter_env + 0.10 * jitter_target
        if self._jitter_env > 0.0:
            jx = np.sin(self.phase_x * 6.4 + t * 11.0)
            jy = np.sin(self.phase_y * 7.1 + t * 13.0)
            jz = np.sin(self.phase_z * 7.8 + t * 9.0)
            jitter = cfg.gravitas_jitter_strength * self._jitter_env * dt
            self.displacement_x += jx * jitter
            self.displacement_y += jy * jitter
            self.displacement_z += jz * jitter

    def _apply_return_mechanic(self, dt: float = 1 / 60):
        """Apply return-to-center force based on configured mechanic.

        Args:
            dt: Time delta for physics integration.

        """
        cfg = self.cfg

        if cfg.gravitas_return_mechanic == "spring":
            self._apply_spring_return(dt)
        elif cfg.gravitas_return_mechanic == "linear":
            self._apply_linear_return(dt)
        else:  # exponential (default)
            self._apply_exponential_return(dt)

    def _apply_spring_return(self, dt: float):
        """Apply spring-based return with bounce effect.

        Args:
            dt: Time delta for physics integration.

        """
        cfg = self.cfg

        # Hooke's law: F = -kx
        spring_force_x = -cfg.gravitas_spring_strength * self.displacement_x
        spring_force_y = -cfg.gravitas_spring_strength * self.displacement_y
        spring_force_z = -cfg.gravitas_spring_strength * self.displacement_z

        # Apply damping to velocity
        self.velocity_x = (
            self.velocity_x * cfg.gravitas_spring_damping
            + spring_force_x * dt / cfg.gravitas_spring_mass
        )
        self.velocity_y = (
            self.velocity_y * cfg.gravitas_spring_damping
            + spring_force_y * dt / cfg.gravitas_spring_mass
        )
        self.velocity_z = (
            self.velocity_z * cfg.gravitas_spring_damping
            + spring_force_z * dt / cfg.gravitas_spring_mass
        )

        # Update displacement
        self.displacement_x += self.velocity_x * dt
        self.displacement_y += self.velocity_y * dt
        self.displacement_z += self.velocity_z * dt

    def _apply_linear_return(self, dt: float):
        """Apply linear damped return with gradual slowdown.

        Args:
            dt: Time delta for physics integration.

        """
        cfg = self.cfg

        # Combined factor: dt-scaled pull toward zero × constant damping
        factor = (1.0 - cfg.gravitas_linear_return_speed * dt) * cfg.gravitas_linear_damping_factor

        self.displacement_x *= factor
        self.displacement_y *= factor
        self.displacement_z *= factor

    def _apply_exponential_return(self, dt: float):
        """Apply exponential decay return with fast-then-slow behavior.

        Args:
            dt: Time delta for physics integration.

        """
        cfg = self.cfg

        # Exponential decay
        decay = np.exp(-cfg.gravitas_exponential_decay_rate * dt * 60)

        self.displacement_x *= decay
        self.displacement_y *= decay
        self.displacement_z *= decay

    def _apply_idle_motion(self, t: float) -> tuple:
        """Apply gentle drift when idle (no breathing).

        Args:
            t: Current time.

        Returns:
            Tuple of (x, y, z) position arrays with drift applied.

        """
        cfg = self.cfg

        # Gentle drift (no audio influence when idle)
        drift_speed = cfg.cloud_drift_speed

        dx = cfg.cloud_drift_amplitude * np.sin(self.phase_x + t * drift_speed)
        dy = cfg.cloud_drift_amplitude * np.sin(self.phase_y + t * drift_speed * 0.7)
        dz = cfg.cloud_drift_amplitude * np.sin(self.phase_z + t * drift_speed * 0.5)

        # Apply displacement from audio + idle drift
        x = self.base_x + self.displacement_x + dx
        y = self.base_y + self.displacement_y + dy
        z = self.base_z + self.displacement_z + dz

        return x, y, z

    def draw(
        self,
        surface,
        t: float,
        audio_level: float,
        audio_bands: tuple[float, float, float] | None = None,
        audio_features: dict | None = None,
    ):
        """Orchestrate rendering with audio-reactive gravity mechanics.

        Args:
            surface: Surface passed to base-class render path.
            t: Current time in seconds.
            audio_level: Broadband RMS level (fallback when bands unavailable).
            audio_bands: (bass, mid, treble) RMS levels from AudioMeter; if None,
                falls back to splitting audio_level equally across all bands.

        """
        # Clamp audio level (AudioMeter caps output at 1.5)
        audio_level = max(0.0, min(audio_level, 1.5))

        if audio_bands is None:
            # Fallback: treat broadband level as uniform across all bands
            audio_bands = (audio_level, audio_level, audio_level)

        # Real dt from elapsed time; first frame falls back to fps target
        if self._last_draw_t is None:
            dt = 1.0 / self.cfg.fps
        else:
            dt = max(t - self._last_draw_t, 1e-4)
        self._last_draw_t = t

        # Apply audio push
        self._apply_audio_push(audio_bands, dt, audio_features=audio_features, t=t)

        # Apply return-to-center mechanics
        self._apply_return_mechanic(dt)

        # Get positions with idle drift
        x, y, z = self._apply_idle_motion(t)

        # Apply rotation
        x, y, z = self._apply_rotation(x, y, z, t)

        # Project to screen
        xs, ys, scale = self._project_to_screen(x, y, z)

        # Compute brightness and sizes
        brightness = self._compute_brightness(scale)
        sizes = self._compute_sizes(brightness)

        keep_mask, size_mul = self._compute_band_modulation(audio_bands, audio_features)
        sizes = sizes * size_mul

        if not np.any(keep_mask):
            return

        xs = xs[keep_mask]
        ys = ys[keep_mask]
        brightness = brightness[keep_mask]
        sizes = sizes[keep_mask]

        # Render
        self._render_points(surface, xs, ys, brightness, sizes)
