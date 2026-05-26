"""Particle Cloud Impact mode - whole-cloud breathing animation.

This module implements the Impact sub-mode of Particle Cloud, featuring
whole-cloud expansion and contraction with gentle drift and rotation.
"""

import numpy as np

from particled.config import Config
from particled.visuals.particle_cloud.base import ParticleCloudBase


class ParticleCloudImpact(ParticleCloudBase):
    """Particle Cloud Impact mode with breathing animation.

    This visualization creates an organic, minimalist particle cloud using Gaussian
    spherical distribution. The entire cloud expands and contracts in a breathing
    motion, with subtle drift for an ethereal, floating appearance.

    Visual characteristics:
    - Pure white particles on black background
    - Gaussian density falloff from center
    - Gentle breathing animation (expansion/contraction)
    - Subtle drift motion for organic feel
    - Slow rotation for spatial awareness
    - Audio-reactive size and motion

    Attributes:
        cfg: Configuration object with all parameters.
        base_x, base_y, base_z: Base particle positions in 3D space.
        phase_x, phase_y, phase_z: Random phase offsets for drift motion.
        density: Precalculated density weights for size variation.

    """

    def __init__(self, cfg: Config):
        """Initialize the Impact mode particle cloud.

        Args:
            cfg: Configuration object containing visualization parameters.

        """
        super().__init__(cfg)
        self._initialize_base_particles()

    def _apply_gentle_motion(self, t: float, audio_level: float) -> tuple:
        """Apply subtle, organic motion to particles.

        Args:
            t: Current time.
            audio_level: Current audio level.

        Returns:
            Tuple of (x, y, z) position arrays.

        """
        cfg = self.cfg

        # Gentle drift and breathing motion with configurable speeds
        drift_speed = cfg.cloud_drift_speed * (
            1.0 + cfg.cloud_audio_drift_boost * audio_level
        )
        breath_speed = cfg.cloud_breath_speed * (
            1.0 + cfg.cloud_audio_breath_boost * audio_level
        )

        # Subtle position offsets with configurable amplitude
        dx = cfg.cloud_drift_amplitude * np.sin(self.phase_x + t * drift_speed)
        dy = cfg.cloud_drift_amplitude * np.sin(self.phase_y + t * drift_speed * 0.7)
        dz = cfg.cloud_drift_amplitude * np.sin(self.phase_z + t * drift_speed * 0.5)

        # Breathing expansion/contraction with configurable amplitude
        breath = (
            1.0 + cfg.cloud_breath_amplitude * np.sin(t * breath_speed) * audio_level
        )

        x = (self.base_x + dx) * breath
        y = (self.base_y + dy) * breath
        z = (self.base_z + dz) * breath

        return x, y, z

    def _compute_sizes_with_audio(
        self, brightness: np.ndarray, audio_level: float
    ) -> np.ndarray:
        """Compute particle sizes with audio boost.

        Args:
            brightness: Brightness values.
            audio_level: Current audio level.

        Returns:
            Array of particle sizes.

        """
        cfg = self.cfg

        # Size varies with density and depth
        base_size = self._compute_sizes(brightness)

        # Configurable audio response
        audio_boost = 1.0 + cfg.cloud_audio_size_boost * audio_level

        return base_size * audio_boost

    def draw(
        self,
        surface,
        t: float,
        audio_level: float,
        audio_bands: tuple[float, float, float] | None = None,
        audio_features: dict | None = None,
    ):
        """Draw the Impact mode particle cloud.

        Args:
            surface: Pygame surface to render to.
            t: Current time in seconds.
            audio_level: Current audio level (0.0-2.0).

        """
        # Clamp audio level
        audio_level = max(0.0, min(audio_level, 2.0))

        # Apply gentle motion
        x, y, z = self._apply_gentle_motion(t, audio_level)

        # Apply slow rotation
        x, y, z = self._apply_rotation(x, y, z, t)

        # Project to screen
        xs, ys, scale = self._project_to_screen(x, y, z)

        # Compute brightness (depth-based)
        brightness = self._compute_brightness(scale)

        # Compute sizes
        sizes = self._compute_sizes_with_audio(brightness, audio_level)

        # Render
        self._render_points(surface, xs, ys, brightness, sizes)
