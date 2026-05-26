"""Base Particle Cloud functionality shared across all modes.

This module provides common particle cloud initialization and rendering logic
that is shared between Impact and Gravitas modes.
"""

import numpy as np

from particled.config import Config
from particled.visuals.base import BaseVisualization


class ParticleCloudBase(BaseVisualization):
    """Base class for Particle Cloud visualizations with shared functionality.

    This abstract class provides common initialization and utility methods
    for all Particle Cloud modes (Impact, Gravitas). It handles:
    - Gaussian spherical particle distribution
    - Phase offset generation for drift animations
    - Density weight calculation
    - Particle position rotation

    Subclasses must implement their specific motion and rendering logic.

    Attributes:
        cfg: Configuration object with all parameters.
        base_x, base_y, base_z: Base particle positions in 3D space.
        phase_x, phase_y, phase_z: Random phase offsets for drift motion.
        density: Precalculated density weights for size variation.

    """

    def __init__(self, cfg: Config):
        """Initialize the base particle cloud.

        Args:
            cfg: Configuration object containing visualization parameters.

        """
        super().__init__(cfg)

    def _initialize_base_particles(self):
        """Initialize base particle positions in spherical cloud.

        Creates a Gaussian spherical distribution of particles with:
        - Random phase offsets for organic drift
        - Density weights for size variation based on distance from center

        Should be called by subclass __init__ methods.

        """
        cfg = self.cfg
        n = cfg.num_particles

        # Generate spherical coordinates with Gaussian distribution
        radius = np.abs(np.random.normal(0, cfg.cloud_density_sigma, n))
        theta = np.random.uniform(0, 2 * np.pi, n)
        phi = np.arccos(2 * np.random.uniform(0, 1, n) - 1)

        # Convert to Cartesian coordinates (base positions)
        self.base_x = radius * np.sin(phi) * np.cos(theta)
        self.base_y = radius * np.sin(phi) * np.sin(theta)
        self.base_z = radius * np.cos(phi)

        # Phase offsets for drift animation
        self.phase_x = np.random.uniform(0, 2 * np.pi, n)
        self.phase_y = np.random.uniform(0, 2 * np.pi, n)
        self.phase_z = np.random.uniform(0, 2 * np.pi, n)

        # Density weights for size variation
        self.density = np.exp(-radius * cfg.cloud_density_falloff)

        max_radius = float(np.max(radius))
        if max_radius <= 0.0:
            max_radius = 1.0
        self.radial_distance = radius / max_radius

        n_bands = max(1, int(cfg.audio_band_count))
        self.band_index = np.clip(
            (self.radial_distance * (n_bands - 1)).astype(np.int32),
            0,
            n_bands - 1,
        )

        # Stable particle gating seed so "count by band" doesn't flicker frame-to-frame.
        self._gate_seed = np.random.random(n)

        return radius  # Return radius for subclass use

    def _resolve_band_levels(
        self,
        audio_bands: tuple[float, float, float] | None,
        audio_features: dict | None,
    ) -> np.ndarray:
        """Return a level vector sized to cfg.audio_band_count."""
        n_bands = max(1, int(self.cfg.audio_band_count))

        mb = None
        if audio_features is not None:
            mb = audio_features.get("bands")
        if mb is not None:
            arr = np.asarray(mb, dtype=np.float32)
            if arr.size >= n_bands:
                return np.clip(arr[:n_bands], 0.0, 1.5)
            if arr.size > 1:
                x_old = np.linspace(0.0, 1.0, arr.size)
                x_new = np.linspace(0.0, 1.0, n_bands)
                return np.clip(np.interp(x_new, x_old, arr), 0.0, 1.5)

        if audio_bands is None:
            audio_bands = (0.0, 0.0, 0.0)

        bass, mid, treble = (float(v) for v in audio_bands)
        anchors = np.array([bass, mid, treble], dtype=np.float32)
        if n_bands == 1:
            return np.array([float(np.mean(anchors))], dtype=np.float32)
        x_old = np.array([0.0, 0.5, 1.0], dtype=np.float32)
        x_new = np.linspace(0.0, 1.0, n_bands)
        return np.clip(np.interp(x_new, x_old, anchors), 0.0, 1.5)

    def _compute_band_modulation(
        self,
        audio_bands: tuple[float, float, float] | None,
        audio_features: dict | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return (keep_mask, size_multiplier) based on per-band controls."""
        levels = self._resolve_band_levels(audio_bands, audio_features)
        count_scales = np.array(self.cfg.get_particle_band_count_scales(), dtype=np.float32)
        size_scales = np.array(self.cfg.get_particle_band_size_scales(), dtype=np.float32)

        # Count control: minimum floor keeps some structure while still allowing dropout.
        presence = np.clip(count_scales * (0.20 + levels), 0.0, 1.0)
        keep_mask = self._gate_seed <= presence[self.band_index]

        # Size control: combine user scale with live energy in each mapped band.
        size_mul = np.clip(size_scales[self.band_index] * (0.70 + levels[self.band_index]), 0.05, 6.0)
        return keep_mask, size_mul

    def _apply_rotation(
        self, x: np.ndarray, y: np.ndarray, z: np.ndarray, t: float
    ) -> tuple:
        """Apply slow rotation for spatial awareness.

        Args:
            x: X coordinates.
            y: Y coordinates.
            z: Z coordinates.
            t: Current time.

        Returns:
            Tuple of rotated (x, y, z) position arrays.

        """
        cfg = self.cfg

        rot_y = t * cfg.cloud_rotation_speed_y
        rot_x = t * cfg.cloud_rotation_speed_x

        cos_y, sin_y = np.cos(rot_y), np.sin(rot_y)
        cos_x, sin_x = np.cos(rot_x), np.sin(rot_x)

        # Rotate around Y
        x1 = cos_y * x + sin_y * z
        z1 = -sin_y * x + cos_y * z

        # Rotate around X
        y2 = cos_x * y - sin_x * z1
        z2 = sin_x * y + cos_x * z1

        return x1, y2, z2

    def _compute_sizes(self, brightness: np.ndarray) -> np.ndarray:
        """Compute particle sizes based on density and depth.

        Args:
            brightness: Brightness values.

        Returns:
            Array of particle sizes.

        """
        cfg = self.cfg

        base_size = (
            cfg.min_point_size
            + (cfg.max_point_size - cfg.min_point_size) * self.density
        )

        return base_size * brightness
