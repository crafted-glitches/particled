"""Particle Cloud Gravitas mode - gravity-centered reactive expansion.

This module implements the Gravitas sub-mode of Particle Cloud, featuring
gravity-centered behavior where audio pushes particles outward from the center,
and they return to their original positions using configurable mechanics.
"""

import numpy as np
import pygame

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
        self._initialize_particles()

    def _initialize_particles(self):
        """Initialize particles with displacement tracking for Gravitas mode."""
        # Initialize base particles (positions, phases, density)
        radius = self._initialize_base_particles()

        cfg = self.cfg
        n = cfg.num_particles

        # Displacement and velocity tracking (for audio-driven movement)
        self.displacement_x = np.zeros(n)
        self.displacement_y = np.zeros(n)
        self.displacement_z = np.zeros(n)
        self.velocity_x = np.zeros(n)
        self.velocity_y = np.zeros(n)
        self.velocity_z = np.zeros(n)

        # Normalized radial distance for frequency band mapping
        max_radius = radius.max() if radius.max() > 0 else 1.0
        self.radial_distance = radius / max_radius

    def _apply_audio_push(self, audio_level: float, dt: float = 1 / 60):
        """Apply outward push force based on audio level and frequency mapping.

        Pushes particles radially outward from center based on audio level.
        Different radial regions respond to different frequency characteristics
        for varied, organic movement.

        Args:
            audio_level: Current audio level (0.0-2.0).
            dt: Time delta for physics integration.

        """
        cfg = self.cfg

        # Apply noise threshold
        effective_audio = max(0.0, audio_level - cfg.audio_noise_threshold)
        if effective_audio <= 0:
            effective_audio = 0.0

        # Frequency band simulation (in absence of real FFT)
        # Bass affects outer particles, treble affects inner particles
        bass_mask = (self.radial_distance >= cfg.gravitas_bass_range[0]) & (
            self.radial_distance <= cfg.gravitas_bass_range[1]
        )
        mid_mask = (self.radial_distance >= cfg.gravitas_mid_range[0]) & (
            self.radial_distance <= cfg.gravitas_mid_range[1]
        )
        treble_mask = (self.radial_distance >= cfg.gravitas_treble_range[0]) & (
            self.radial_distance <= cfg.gravitas_treble_range[1]
        )

        # Simulated frequency response (bass = 0.7, mid = 1.0, treble = 0.5)
        freq_response = np.ones_like(self.radial_distance)
        freq_response[bass_mask] *= 0.7 + 0.3 * effective_audio
        freq_response[mid_mask] *= 1.0 * effective_audio
        freq_response[treble_mask] *= 0.5 + 0.5 * effective_audio

        # Calculate push force radially outward
        push_strength = cfg.gravitas_push_strength * freq_response * effective_audio

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

        # Linear return with damping
        return_force = cfg.gravitas_linear_return_speed * dt

        self.displacement_x *= 1.0 - return_force
        self.displacement_y *= 1.0 - return_force
        self.displacement_z *= 1.0 - return_force

        # Apply additional damping
        self.displacement_x *= cfg.gravitas_linear_damping_factor
        self.displacement_y *= cfg.gravitas_linear_damping_factor
        self.displacement_z *= cfg.gravitas_linear_damping_factor

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

    def draw(self, surface: pygame.Surface, t: float, audio_level: float):
        """Orchestrate rendering with audio-reactive gravity mechanics.

        Args:
            surface: Pygame surface to render to.
            t: Current time in seconds.
            audio_level: Current audio level (0.0-2.0).

        """
        # Clamp audio level
        audio_level = max(0.0, min(audio_level, 2.0))

        # Physics update (60 FPS assumption)
        dt = 1 / 60

        # Apply audio push
        self._apply_audio_push(audio_level, dt)

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

        # Render
        self._render_points(surface, xs, ys, brightness, sizes)
