"""Penrose Triangle visualization with impossible geometry illusion.

Based on SVG '7'-shaped polygons rotated to form proper Penrose tribar.
"""

import math
import random

import numpy as np

from particled.config import Config
from particled.visuals.base import BaseVisualization


class PenroseTriangle(BaseVisualization):
    """Penrose Triangle using proper '7'-shaped beam geometry."""

    def __init__(self, cfg: Config) -> None:
        """Initialize Penrose Triangle visualization.

        Args:
            cfg: Configuration object with visualization parameters.

        """
        super().__init__(cfg)

        # Build the three '7'-shaped polygons
        self.polygons = self._build_penrose_polygons()

        # Fill polygons with particles
        self.particles = self._build_particles()

        # Brightness levels for the three beams (grayscale)
        self.beam_brightness = [240, 190, 130]

    @staticmethod
    def _rotate_point(x: float, y: float, angle_rad: float) -> tuple:
        """Rotate point around origin.

        Args:
            x: X coordinate.
            y: Y coordinate.
            angle_rad: Rotation angle in radians.

        Returns:
            Tuple of rotated (x, y).

        """
        ca = math.cos(angle_rad)
        sa = math.sin(angle_rad)
        return x * ca - y * sa, x * sa + y * ca

    @staticmethod
    def _point_in_polygon(x: float, y: float, polygon: list) -> bool:
        """Test if point is inside polygon using ray casting.

        Args:
            x: X coordinate.
            y: Y coordinate.
            polygon: List of (x, y) vertices.

        Returns:
            True if point is inside polygon.

        """
        inside = False
        n = len(polygon)
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            intersect = ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-9) + xi
            )
            if intersect:
                inside = not inside
            j = i
        return inside

    def _build_penrose_polygons(self) -> list:
        """Build three '7'-shaped polygons forming Penrose tribar.

        Returns:
            List of three polygons, each as list of (x, y) tuples.

        """
        # Base '7' shape from SVG (accurate Penrose coordinates)
        base_points = [
            (-53.0, -378.0),
            (53.0, -378.0),
            (354.0, 143.0),
            (-140.0, 143.0),
            (-87.0, 50.0),
            (191.0, 50.0),
        ]

        # Rotate the base shape at 0°, 120°, 240° (don't modify base coords)
        rotated_polys = []
        for angle_deg in (0.0, 120.0, 240.0):
            angle_rad = math.radians(angle_deg)
            poly = [self._rotate_point(x, y, angle_rad) for (x, y) in base_points]
            rotated_polys.append(poly)

        # Compute an area-weighted centroid of the three polygons
        def poly_area_centroid(poly):
            area = 0.0
            cx_acc = 0.0
            cy_acc = 0.0
            n = len(poly)
            area_epsilon = 1e-9
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % n]
                cross = x1 * y2 - x2 * y1
                area += cross
                cx_acc += (x1 + x2) * cross
                cy_acc += (y1 + y2) * cross
            area *= 0.5
            if abs(area) < area_epsilon:
                return 0.0, 0.0, 0.0
            cx = cx_acc / (6.0 * area)
            cy = cy_acc / (6.0 * area)
            return abs(area), cx, cy

        total_area = 0.0
        cx_weighted = 0.0
        cy_weighted = 0.0
        all_points = []
        for poly in rotated_polys:
            area, pcx, pcy = poly_area_centroid(poly)
            total_area += area
            cx_weighted += pcx * area
            cy_weighted += pcy * area
            all_points.extend(poly)

        if total_area > 0:
            cx = cx_weighted / total_area
            cy = cy_weighted / total_area
        else:
            xs_tmp = [x for x, _ in all_points]
            ys_tmp = [y for _, y in all_points]
            cx = (min(xs_tmp) + max(xs_tmp)) / 2.0
            cy = (min(ys_tmp) + max(ys_tmp)) / 2.0

        xs = [x for x, _ in all_points]
        ys = [y for _, y in all_points]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)

        # Scale to fit in window with some padding
        scale_factor = self.cfg.penrose_triangle_scale / 400.0
        scale = (
            scale_factor * 0.8 * min(self.cfg.width / width, self.cfg.height / height)
        )

        # Transform to screen coordinates centered at window center
        screen_polys = []
        for poly in rotated_polys:
            transformed = []
            for x, y in poly:
                sx = (x - cx) * scale + self.cfg.width / 2.0
                sy = (y - cy) * scale + self.cfg.height / 2.0
                transformed.append((sx, sy))
            screen_polys.append(transformed)

        # Final recentroid in screen space to counter any residual drift
        # (numerical differences between SVG center and visual center).
        def poly_area_centroid(poly):
            area = 0.0
            cx_acc = 0.0
            cy_acc = 0.0
            n = len(poly)
            area_epsilon = 1e-9
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % n]
                cross = x1 * y2 - x2 * y1
                area += cross
                cx_acc += (x1 + x2) * cross
                cy_acc += (y1 + y2) * cross
            area *= 0.5
            if abs(area) < area_epsilon:
                return 0.0, 0.0, 0.0
            cx_local = cx_acc / (6.0 * area)
            cy_local = cy_acc / (6.0 * area)
            return abs(area), cx_local, cy_local

        total_area = 0.0
        cx_weighted = 0.0
        cy_weighted = 0.0
        for poly in screen_polys:
            area, pcx, pcy = poly_area_centroid(poly)
            total_area += area
            cx_weighted += pcx * area
            cy_weighted += pcy * area

        if total_area > 0:
            cx_screen = cx_weighted / total_area
            cy_screen = cy_weighted / total_area
            dx = self.cfg.width / 2.0 - cx_screen
            dy = self.cfg.height / 2.0 - cy_screen
            screen_polys = [
                [(sx + dx, sy + dy) for (sx, sy) in poly] for poly in screen_polys
            ]

        return screen_polys

    def _build_particles(self) -> list:
        """Fill each polygon with particles on a grid.

        Returns:
            List of particle dictionaries.

        """
        particles = []
        spacing = max(1, int(20000 / self.cfg.num_particles))

        for beam_index, poly in enumerate(self.polygons):
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            y = min_y
            while y <= max_y:
                x = min_x
                while x <= max_x:
                    if self._point_in_polygon(x, y, poly):
                        # Calculate center of this beam
                        beam_xs = [p[0] for p in poly]
                        beam_ys = [p[1] for p in poly]
                        beam_cx = sum(beam_xs) / len(beam_xs)
                        beam_cy = sum(beam_ys) / len(beam_ys)

                        # Direction from beam center to particle (outward)
                        dx = x - beam_cx
                        dy = y - beam_cy
                        direction = math.atan2(dy, dx)

                        particles.append(
                            {
                                "base_x": x,
                                "base_y": y,
                                "x": x,
                                "y": y,
                                "beam_index": beam_index,
                                "beam_cx": beam_cx,
                                "beam_cy": beam_cy,
                                "phase": random.uniform(0, 2 * math.pi),
                                "speed": random.uniform(0.5, 1.5),
                                "direction": direction,
                                "displacement_x": 0.0,
                                "displacement_y": 0.0,
                                "velocity_x": 0.0,
                                "velocity_y": 0.0,
                            }
                        )
                    x += spacing
                y += spacing

        return particles

    def _update_particles(self, t: float, audio_level: float):
        """Update particle positions based on audio using spring physics.

        Args:
            t: Current time.
            audio_level: Current audio level.

        """
        dt = 1.0 / 60.0  # 60 FPS
        cfg = self.cfg

        # Spring physics parameters (similar to Gravitas)
        spring_strength = cfg.penrose_fold_strength * 0.1
        spring_damping = 0.85
        spring_mass = 1.0
        push_strength = cfg.penrose_audio_push * (cfg.penrose_particle_spread / 10.0)
        max_displacement = cfg.penrose_particle_spread
        audio_threshold = 0.05

        for p in self.particles:
            # Apply audio push outward from base position
            if audio_level > audio_threshold:
                push_force = push_strength * audio_level * dt
                p["displacement_x"] += math.cos(p["direction"]) * push_force
                p["displacement_y"] += math.sin(p["direction"]) * push_force

            # Spring force pulling back to base (Hooke's law: F = -kx)
            spring_force_x = -spring_strength * p["displacement_x"]
            spring_force_y = -spring_strength * p["displacement_y"]

            # Update velocity with spring force and damping
            p["velocity_x"] = (
                p["velocity_x"] * spring_damping + spring_force_x * dt / spring_mass
            )
            p["velocity_y"] = (
                p["velocity_y"] * spring_damping + spring_force_y * dt / spring_mass
            )

            # Update displacement from velocity
            p["displacement_x"] += p["velocity_x"] * dt
            p["displacement_y"] += p["velocity_y"] * dt

            # Clamp displacement to preserve the Penrose silhouette
            disp_mag = math.hypot(p["displacement_x"], p["displacement_y"])
            if disp_mag > max_displacement:
                scale_back = max_displacement / disp_mag
                p["displacement_x"] *= scale_back
                p["displacement_y"] *= scale_back

            # Update actual position (base + displacement)
            p["x"] = p["base_x"] + p["displacement_x"]
            p["y"] = p["base_y"] + p["displacement_y"]

    def draw(self, surface, t: float, audio_level: float, audio_bands: tuple[float, float, float] | None = None):
        """Render the Penrose triangle visualization.

        Args:
            surface: Surface to render to (used by base-class CPU path only;
                     in GL mode the GLRenderer handles output directly).
            t: Current time.
            audio_level: Current audio level.

        """
        # Update particle positions
        self._update_particles(t, audio_level)

        n = len(self.particles)
        xs = np.empty(n, dtype=np.float32)
        ys = np.empty(n, dtype=np.float32)
        brightnesses = np.empty(n, dtype=np.float32)
        sizes = np.empty(n, dtype=np.float32)

        base_size = 2.0
        for i, p in enumerate(self.particles):
            base_brightness = self.beam_brightness[p["beam_index"]]
            displacement_mag = math.sqrt(
                p["displacement_x"] ** 2 + p["displacement_y"] ** 2
            )
            audio_boost = audio_level * self.cfg.audio_gain * 0.5
            displacement_boost = min(30.0, displacement_mag * 0.5)

            brightness = max(0.0, min(255.0, base_brightness + audio_boost + displacement_boost))
            size = max(1.0, base_size + audio_level * self.cfg.audio_gain * 0.05)

            xs[i] = p["x"]
            ys[i] = p["y"]
            brightnesses[i] = brightness / 255.0
            sizes[i] = size

        self._render_points(surface, xs, ys, brightnesses, sizes)
