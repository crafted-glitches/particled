"""Base visualization utilities for rendering particle systems.

This module provides the foundational classes and utilities for all particle
visualizations in the system. It defines the abstract base class that all
visualization styles must inherit from, along with shared helper functions
for common rendering operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

import numpy as np
from particled import compat as pygame

from particled.config import Config

if TYPE_CHECKING:
    from particled.visuals.gl_renderer import GLRenderer

# ── module-level caches (no per-frame allocation) ─────────────────────────────

# Reused fade surface — recreated only when window is resized.
_fade_surf: pygame.Surface | None = None
_fade_surf_size: tuple[int, int] = (0, 0)

# 256-entry grayscale lookup table mapping intensity → packed pixel value.
# Built once on first render call; valid for the lifetime of the display surface
# since the pixel format doesn't change between resizes.
_gray_lut: np.ndarray | None = None


def _get_gray_lut(surface: pygame.Surface) -> np.ndarray:
    """Return (building if needed) the 256-entry grayscale → packed pixel LUT."""
    global _gray_lut
    if _gray_lut is None:
        _gray_lut = np.array(
            [surface.map_rgb(i, i, i) for i in range(256)], dtype=np.uint32
        )
    return _gray_lut


class BaseVisualization(ABC):
    """Abstract base class defining the interface for particle visualizations.

    Set ``BaseVisualization.gl_renderer`` to a :class:`GLRenderer` instance
    before creating any visualization to enable GPU rendering for all subclasses.

    This class provides a common foundation for all visualization styles,
    offering shared utility methods for 3D projection, brightness computation,
    and particle rendering. Subclasses must implement the abstract `draw` method
    to define their specific visual behavior.

    The base class handles:
    - 3D to 2D screen projection with perspective
    - Depth-based brightness calculation with gamma correction
    - Efficient batch rendering of particles as circles

    Attributes:
        cfg: Configuration object containing all visualization parameters.

    Methods to Override:
        draw: Main rendering method that orchestrates the visualization.

    Utility Methods (available to subclasses):
        _project_to_screen: Convert 3D coordinates to screen space.
        _compute_brightness: Calculate brightness from depth values.
        _render_points: Draw all particles to the surface.

    Example:
        >>> class MyVisualization(BaseVisualization):
        ...     def draw(self, surface, t, audio_level):
        ...         # Create particle positions
        ...         x, y, z = self._generate_positions(t)
        ...         # Project to screen
        ...         xs, ys, scale = self._project_to_screen(x, y, z)
        ...         # Compute visual properties
        ...         brightness = self._compute_brightness(scale)
        ...         sizes = np.ones_like(brightness) * 2
        ...         # Render
        ...         self._render_points(surface, xs, ys, brightness, sizes)

    """

    gl_renderer: ClassVar[GLRenderer | None] = None
    """Shared GPU renderer. Set before instantiating visualizations to enable
    OpenGL rendering for all subclasses. None = use pygame CPU path."""

    def __init__(self, cfg: Config):
        """Initialize the visualization with configuration.

        Stores the configuration object for use by all visualization methods.
        Subclasses should call super().__init__(cfg) before performing their
        own initialization.

        Args:
            cfg: Configuration object containing all visualization parameters
                including window size, particle counts, colors, and style-specific
                settings.

        """
        self.cfg = cfg

    @abstractmethod
    def draw(self, surface: pygame.Surface, t: float, audio_level: float, audio_bands: tuple[float, float, float] | None = None):
        """Render the visualization to pygame surface.

        Must be implemented by subclasses.

        This is the main entry point for rendering called once per frame. Subclasses
        must implement this method to define their visual behavior, typically following
        this pattern:
        1. Generate or update particle positions based on time and audio
        2. Apply transformations (rotation, distortion, etc.)
        3. Project 3D coordinates to 2D screen space
        4. Compute visual properties (brightness, size, color)
        5. Render particles to the surface

        Args:
            surface: Pygame surface to render to. Drawing directly modifies
                this surface.
            t: Current time in seconds since visualization start. Used for
                animations and time-based effects.
            audio_level: Current audio level from the microphone, typically in range
                0.0-2.0 where 0.0 is silence and 1.0 is moderate input. Can be used
                to drive reactive visual effects.

        """

    def _project_to_screen(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple:
        """Project 3D coordinates to 2D screen space using perspective projection.

        Applies perspective transformation to convert 3D world coordinates to 2D
        screen pixel coordinates. Uses field-of-view based scaling to create depth
        perception, with more distant objects appearing smaller.

        The projection formula:
        - Add z_offset to z coordinates (moves objects away from camera)
        - Scale factor = fov / (fov + z)
        - Screen X = center_x + x * scale * pixel_scale
        - Screen Y = center_y + y * scale * pixel_scale

        Args:
            x: Array of X coordinates in 3D world space.
            y: Array of Y coordinates in 3D world space.
            z: Array of Z coordinates in 3D world space (depth).

        Returns:
            Tuple of (xs, ys, scale) where:
            - xs: Array of X coordinates in screen pixel space.
            - ys: Array of Y coordinates in screen pixel space.
            - scale: Array of perspective scale factors (0.0-1.0) indicating
              relative depth, with larger values being closer to camera.

        """
        cfg = self.cfg

        z = z + cfg.z_offset  # new array — do not mutate caller's z
        scale = cfg.fov / (cfg.fov + z)

        xs = cfg.width * 0.5 + x * scale * cfg.pixel_scale
        ys = cfg.height * 0.5 + y * scale * cfg.pixel_scale

        return xs, ys, scale

    def _compute_brightness(self, scale: np.ndarray) -> np.ndarray:
        """Compute brightness values based on depth using gamma correction.

        Converts depth scale values to brightness intensities, with closer objects
        appearing brighter. Applies gamma correction to control the brightness
        distribution and enhance visual contrast.

        The computation:
        1. Normalize scale values to 0.0-1.0 range (relative to maximum depth)
        2. Apply gamma correction: brightness = normalized_scale ^ gamma
        3. Clamp results to valid range [0.0, 1.0]

        Higher gamma values (>1.0) create more contrast with brighter highlights
        and darker shadows. Lower gamma values (<1.0) create more even lighting.

        Args:
            scale: Array of perspective scale factors from _project_to_screen,
                where larger values represent objects closer to the camera.

        Returns:
            Array of brightness values in range 0.0-1.0, where 1.0 is full
            brightness (white) and 0.0 is completely dark (black).

        """
        cfg = self.cfg
        return np.clip(scale / scale.max(), 0.0, 1.0) ** cfg.brightness_gamma

    def _render_points(
        self,
        surface: pygame.Surface,
        xs: np.ndarray,
        ys: np.ndarray,
        brightness: np.ndarray,
        sizes: np.ndarray,
    ):
        """Render all particles as circles to the pygame surface.

        Draws each particle as a filled circle at the specified screen coordinates,
        with grayscale color based on brightness and variable size. Only renders
        particles that fall within the visible screen bounds for efficiency.

        The rendering process:
        1. Iterate through all particles
        2. Skip particles outside screen bounds
        3. Convert brightness to grayscale RGB (0-255)
        4. Draw filled circle at integer pixel coordinates
        5. Ensure minimum size of 1 pixel

        Args:
            surface: Pygame surface to draw particles on. Modified in-place.
            xs: Array of X screen coordinates in pixels.
            ys: Array of Y screen coordinates in pixels.
            brightness: Array of brightness values (0.0-1.0) for each particle.
                0.0 renders as black, 1.0 as white.
            sizes: Array of particle radii in pixels. Values are clamped to
                minimum of 1 pixel and converted to integers.

        Performance:
            Uses boundary checking to avoid rendering off-screen particles.
            For large particle counts (>10000), consider spatial indexing
            or view frustum culling for better performance.

        """
        if self.gl_renderer is not None:
            self.gl_renderer.render(xs, ys, brightness, sizes)
            return

        cfg = self.cfg
        w, h = cfg.width, cfg.height

        int_sizes = np.maximum(np.round(sizes).astype(np.int32), 1)

        # Vectorised visibility check — avoids a Python-level `if` per particle.
        visible = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)

        # Fast path: size-1 particles written directly into the pixel buffer via
        # surfarray. Avoids 7000+ draw.circle calls/frame for the common case.
        tiny_mask = visible & (int_sizes <= 1)
        if tiny_mask.any():
            lut = _get_gray_lut(surface)
            intensities = np.clip(brightness[tiny_mask] * 255, 0, 255).astype(np.uint8)
            px_arr = pygame.surfarray.pixels2d(surface)
            px_arr[xs[tiny_mask].astype(np.int32), ys[tiny_mask].astype(np.int32)] = lut[intensities]
            del px_arr  # release surface lock

        # Slow path: larger circles — loop only over visible, non-tiny particles.
        large_mask = visible & (int_sizes > 1)
        if large_mask.any():
            lxs = xs[large_mask].astype(np.int32)
            lys = ys[large_mask].astype(np.int32)
            lbr = brightness[large_mask]
            lsz = int_sizes[large_mask]
            for px, py, b, s in zip(lxs, lys, lbr, lsz):
                intensity = int(255 * b)
                pygame.draw.circle(surface, (intensity, intensity, intensity), (int(px), int(py)), int(s))


def fade_surface(surface: pygame.Surface, alpha: int):
    """Create motion trail effect by applying semi-transparent black overlay.

    Gradually fades the existing surface content by drawing a semi-transparent
    black rectangle over it. This creates motion trails as particles move,
    with previous frames slowly fading out.

    The fade effect:
    - alpha=0: No fading, particles leave permanent trails (surface fills up)
    - alpha=1-50: Slow fade, long flowing trails (ethereal effect)
    - alpha=51-150: Medium fade, balanced motion trails
    - alpha=151-254: Fast fade, short trails or minimal blur
    - alpha=255: Instant clear, no trails (sharp, clean rendering)

    This is typically called once per frame before rendering new particles.

    Args:
        surface: Pygame surface to apply the fade effect to. Modified in-place.
        alpha: Opacity of the black overlay (0-255). Higher values create faster
            fading and shorter trails. 0 disables fading entirely.

    Performance:
        Uses pygame SRCALPHA blending which is hardware-accelerated on most systems.
        Negligible performance impact compared to particle rendering.

    Example:
        >>> # In main rendering loop
        >>> fade_surface(screen, cfg.fade_alpha)  # Apply trails
        >>> visualization.draw(screen, t, audio_level)  # Draw new frame
        >>> pygame.display.flip()

    """
    if alpha <= 0:
        return
    global _fade_surf, _fade_surf_size
    size = surface.get_size()
    if _fade_surf is None or _fade_surf_size != size:
        _fade_surf = pygame.Surface(size, pygame.SRCALPHA)
        _fade_surf_size = size
    _fade_surf.fill((0, 0, 0, alpha))
    surface.blit(_fade_surf, (0, 0))
