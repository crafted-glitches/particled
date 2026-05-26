"""Torus Knot visualization - complex mathematical knot patterns."""

import math

import numpy as np

from particled.config import Config
from particled.visuals.base import BaseVisualization


class TorusKnotField(BaseVisualization):
    """Generates and draws a reactive torus-knot style point cloud."""

    def __init__(self, cfg: Config):
        """Initialize the torus knot field.

        Args:
            cfg: Configuration object containing visualization parameters.

        """
        super().__init__(cfg)
        # parameter for each particle along [0, 2π)
        self.u = np.linspace(0.0, 2.0 * math.pi, cfg.num_particles, endpoint=False)
        # per-point phase offset so it feels more organic
        self.phase = np.random.uniform(0.0, 2.0 * math.pi, cfg.num_particles)

    def _compute_torus_knot_positions(
        self, u: np.ndarray, t: float, radius: float
    ) -> tuple:
        """Compute base torus-knot 3D positions.

        Args:
            u: Parameter array for particle positions.
            t: Time parameter.
            radius: Base radius of the torus.

        Returns:
            Tuple of (x, y, z) position arrays.

        """
        cfg = self.cfg
        phase2 = 0.6 * t

        cos_nu = np.cos(cfg.knot_nu * u + phase2)
        sin_nu = np.sin(cfg.knot_nu * u + phase2)

        x = (radius + cfg.tube_radius * cos_nu) * np.cos(cfg.knot_mu * u)
        y = (radius + cfg.tube_radius * cos_nu) * np.sin(cfg.knot_mu * u)
        z = cfg.tube_radius * sin_nu

        return x, y, z

    def _apply_distortion(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        *,
        u: np.ndarray,
        t: float,
        audio_level: float,
    ) -> tuple:
        """Apply audio-driven distortion to positions.

        Args:
            x: X coordinates.
            y: Y coordinates.
            z: Z coordinates.
            u: Parameter array.
            t: Time parameter.
            audio_level: Current audio level.

        Returns:
            Tuple of distorted (x, y, z) position arrays.

        """
        cfg = self.cfg
        distortion = cfg.audio_distortion_scale * audio_level

        if distortion > 0.0:
            wobble = np.sin(
                cfg.distortion_freq * u + self.phase + t * cfg.distortion_speed
            )
            x += distortion * wobble * 0.7
            y += distortion * wobble * 0.4
            z += distortion * wobble * 0.9

        return x, y, z

    def _rotate_3d(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        *,
        t: float,
        audio_level: float,
    ) -> tuple:
        """Apply 3D rotation around X and Y axes.

        Args:
            x: X coordinates.
            y: Y coordinates.
            z: Z coordinates.
            t: Time parameter.
            audio_level: Current audio level.

        Returns:
            Tuple of rotated (x, y, z) position arrays.

        """
        cfg = self.cfg

        rot_y = (
            cfg.base_rotation_speed_y
            * (1.0 + cfg.audio_rotation_boost * audio_level)
            * t
        )
        rot_x = cfg.base_rotation_speed_x * (1.0 + 0.7 * audio_level) * t

        cos_y, sin_y = math.cos(rot_y), math.sin(rot_y)
        cos_x, sin_x = math.cos(rot_x), math.sin(rot_x)

        # Rotate around Y
        x1 = cos_y * x + sin_y * z
        z1 = -sin_y * x + cos_y * z

        # Rotate around X
        y2 = cos_x * y - sin_x * z1
        z2 = sin_x * y + cos_x * z1

        return x1, y2, z2

    def _compute_sizes(self, brightness: np.ndarray) -> np.ndarray:
        """Compute particle sizes based on brightness.

        Args:
            brightness: Brightness values.

        Returns:
            Array of particle sizes.

        """
        cfg = self.cfg
        return (
            cfg.min_point_size + (cfg.max_point_size - cfg.min_point_size) * brightness
        )

    def draw(
        self,
        surface,
        t: float,
        audio_level: float,
        audio_bands: tuple[float, float, float] | None = None,
        audio_features: dict | None = None,
    ):
        """Orchestrate all rendering steps and draw the torus knot.

        Args:
            surface: Pygame surface to render to.
            t: Current time.
            audio_level: Current audio level.

        """
        cfg = self.cfg

        # Time-evolving parameter
        u = self.u + t * cfg.distortion_speed

        # Audio influence
        audio_level = max(0.0, min(audio_level, 2.0))
        radius = cfg.base_radius * (1.0 + cfg.audio_radius_scale * audio_level)

        # Compute geometry
        x, y, z = self._compute_torus_knot_positions(u, t, radius)
        x, y, z = self._apply_distortion(x, y, z, u=u, t=t, audio_level=audio_level)
        x, y, z = self._rotate_3d(x, y, z, t=t, audio_level=audio_level)

        # Project to screen
        xs, ys, scale = self._project_to_screen(x, y, z)

        # Compute visual properties
        brightness = self._compute_brightness(scale)
        sizes = self._compute_sizes(brightness)

        # Render
        self._render_points(surface, xs, ys, brightness, sizes)
