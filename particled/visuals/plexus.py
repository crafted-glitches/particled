"""Plexus mesh visualization - a crumpled, audio-reactive wireframe network.

Renders a cloud of nodes arranged on a Fibonacci sphere lattice, displaced by
continuously evolving 3-D fractal noise so the whole shape looks like a
hand-crumpled wire ball, and connected by a dense web of short
(nearest-neighbor) and long ("chord") edges. Audio drives how many of those
edges are currently visible, how strongly the mesh crumples, and how bright
it flashes on onsets - producing the "tangled wireframe network" look.
"""

from __future__ import annotations

import numpy as np

from particled.config import Config
from particled.visuals.base import BaseVisualization
from particled.visuals.noise import fbm3


class PlexusField(BaseVisualization):
    """Crumpled wireframe mesh with audio-reactive connection density.

    Visual characteristics:
    - Nodes are uniformly distributed on a sphere (Fibonacci lattice), then
      continuously displaced by fractal noise to form an irregular, faceted,
      slowly writhing "crumpled paper ball" silhouette.
    - A fixed candidate graph (nearest-neighbor "shell" links + random
      long-range "chord" links) is built once at init; each frame, only the
      edges currently shorter than a dynamic, audio-reactive threshold are
      drawn, so the web visibly densifies with louder audio and on onsets.
    - Depth-based brightness (shared with every other style) plus an
      audio/onset brightness boost make loud moments visibly flash.
    - Every building block - node count, per-node noise, edge topology, edge
      visibility/width/opacity, whole-mesh motion, and per-band audio
      reactivity - is independently configurable (see ``Config`` attributes
      prefixed ``plexus_``).

    Attributes:
        cfg: Configuration object with all parameters.
        node_count: Actual number of nodes in use (capped for performance).
        base_x, base_y, base_z: Static unit-sphere node positions (pre-noise).
        phase: Per-node random phase offsets used for fine jitter.
        edge_i, edge_j: Node index arrays for the candidate edge graph.

    """

    # Hard cap so the O(n^2)-ish candidate-graph construction (done once, at
    # init) and per-frame edge count stay fast regardless of the shared
    # "Particles" slider value, which every other style also repurposes.
    _MAX_NODES = 3000

    def __init__(self, cfg: Config):
        """Initialize node positions and the candidate connection graph.

        Args:
            cfg: Configuration object containing visualization parameters.

        """
        super().__init__(cfg)

        self.node_count = max(8, min(int(cfg.num_particles), self._MAX_NODES))
        self.base_x, self.base_y, self.base_z = self._build_base_nodes(self.node_count)

        rng = np.random.default_rng()
        self._seed_offset = int(rng.integers(0, 1_000_000))
        self.phase = rng.uniform(0.0, 2.0 * np.pi, self.node_count)

        self.edge_i, self.edge_j, self._mean_edge_length = self._build_candidate_edges(
            self.base_x, self.base_y, self.base_z,
            k=max(1, int(cfg.plexus_knn_links)),
            chord_ratio=max(0.0, float(cfg.plexus_chord_link_ratio)),
        )

        # Slow-decaying envelopes for audio-reactive motion, following the
        # same smoothed-envelope pattern used by ParticleCloudGravitas.
        self._flash_env = 0.0
        self._swirl_env = 0.0
        self._jitter_env = 0.0
        self._level_env = 0.0
        self._rot = np.zeros(3)
        self._last_t: float | None = None

    @staticmethod
    def _build_base_nodes(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return unit-sphere node positions via a Fibonacci lattice.

        Produces a near-uniform point distribution with no pole clustering,
        which keeps candidate edge lengths consistent across the mesh.

        Args:
            n: Number of nodes to generate.

        Returns:
            Tuple of (x, y, z) unit-sphere coordinate arrays.

        """
        i = np.arange(n, dtype=np.float64)
        golden_angle = np.pi * (3.0 - np.sqrt(5.0))
        z = 1.0 - (2.0 * i + 1.0) / n
        radius_xy = np.sqrt(np.clip(1.0 - z * z, 0.0, 1.0))
        theta = i * golden_angle
        x = radius_xy * np.cos(theta)
        y = radius_xy * np.sin(theta)
        return x, y, z

    @staticmethod
    def _build_candidate_edges(
        bx: np.ndarray, by: np.ndarray, bz: np.ndarray, k: int, chord_ratio: float
    ) -> tuple[np.ndarray, np.ndarray, float]:
        """Build the fixed candidate graph: k-NN "shell" + random "chord" links.

        Computed once from the static base positions, in memory-bounded
        chunks, so the cost stays reasonable even for several thousand nodes.
        The k-NN links reproduce the low-poly faceted hull silhouette; the
        chord links add the long diagonal lines that cross through the
        volume. Visibility of each candidate edge is then decided per-frame
        by ``draw()`` based on live (noise + audio displaced) distance.

        Args:
            bx, by, bz: Static unit-sphere node positions.
            k: Number of nearest-neighbor links to keep per node.
            chord_ratio: Extra random long-range links, as a fraction of n.

        Returns:
            Tuple of (edge_i, edge_j, mean_edge_length): endpoint index
            arrays for every candidate edge, and the mean Euclidean length of
            those edges at rest (used to scale the visibility threshold so
            it self-adjusts to node count / base radius / link density).

        """
        n = len(bx)
        if n < 2:
            return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), 1.0

        pts = np.stack([bx, by, bz], axis=1)
        k = max(1, min(k, n - 1))

        edge_set: set[tuple[int, int]] = set()
        chunk = 512
        for start in range(0, n, chunk):
            end = min(start + chunk, n)
            sub = pts[start:end]
            d2 = np.sum((sub[:, None, :] - pts[None, :, :]) ** 2, axis=2)
            local_idx = np.arange(end - start)
            d2[local_idx, start + local_idx] = np.inf
            nn_idx = np.argpartition(d2, kth=k - 1, axis=1)[:, :k]
            for li, gi in enumerate(range(start, end)):
                for j in nn_idx[li]:
                    a, b = (gi, int(j)) if gi < j else (int(j), gi)
                    edge_set.add((a, b))

        chord_count = int(n * chord_ratio)
        if chord_count > 0:
            rng = np.random.default_rng()
            ai = rng.integers(0, n, size=chord_count)
            bi = rng.integers(0, n, size=chord_count)
            for a, b in zip(ai, bi, strict=True):
                if a == b:
                    continue
                lo, hi = (int(a), int(b)) if a < b else (int(b), int(a))
                edge_set.add((lo, hi))

        if not edge_set:
            return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), 1.0

        edges = np.array(sorted(edge_set), dtype=np.int32)
        edge_i, edge_j = edges[:, 0], edges[:, 1]
        lengths = np.sqrt(
            (bx[edge_i] - bx[edge_j]) ** 2
            + (by[edge_i] - by[edge_j]) ** 2
            + (bz[edge_i] - bz[edge_j]) ** 2
        )
        mean_length = float(np.mean(lengths)) if len(lengths) else 1.0
        return edge_i, edge_j, max(mean_length, 1e-6)

    def _resolve_bass_mid_treble(
        self,
        audio_bands: tuple[float, float, float] | None,
        audio_features: dict | None,
    ) -> tuple[float, float, float]:
        """Return (bass, mid, treble) envelope values above the noise floor."""
        cfg = self.cfg
        bands_arr = None
        if audio_features is not None:
            mb = audio_features.get("bands")
            if mb is not None and len(mb) > 0:
                bands_arr = np.asarray(mb, dtype=np.float64)

        if bands_arr is not None:
            n = len(bands_arr)
            if n >= 3:
                lo = max(1, n // 3)
                hi = max(lo + 1, (2 * n) // 3)
                bass = float(np.mean(bands_arr[:lo]))
                mid = float(np.mean(bands_arr[lo:hi]))
                treble = float(np.mean(bands_arr[hi:]))
            else:
                bass = mid = treble = float(np.mean(bands_arr))
        elif audio_bands is not None:
            bass, mid, treble = (float(v) for v in audio_bands)
        else:
            bass = mid = treble = 0.0

        threshold = cfg.audio_noise_threshold
        return (
            max(0.0, bass - threshold),
            max(0.0, mid - threshold),
            max(0.0, treble - threshold),
        )

    def _compute_crumple_displacement(
        self, t: float, amplitude: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return the organic noise-driven (dx, dy, dz) displacement per node.

        Samples fractal noise at each node's base position, shifted through a
        slowly advancing offset to fake continuous 4-D (space + time) noise
        without a dedicated 4-D implementation. A radial component bulges or
        dents the sphere (the "crumpled paper" look); a tangential component
        adds extra chaos so facets don't stay perfectly spherical.

        Args:
            t: Current time in seconds.
            amplitude: Displacement magnitude (already audio-boosted).

        Returns:
            Tuple of (dx, dy, dz) displacement arrays, one entry per node.

        """
        cfg = self.cfg
        freq = cfg.plexus_crumple_frequency
        evolve = cfg.plexus_crumple_evolve_speed
        time_offset = np.array([t * 0.37, t * 0.21, t * 0.53]) * evolve

        base_pos = np.stack([self.base_x, self.base_y, self.base_z], axis=1)
        pos = base_pos * freq + time_offset
        octaves = cfg.plexus_crumple_octaves
        radial_noise = fbm3(pos, octaves=octaves, seed=self._seed_offset)

        dx = self.base_x * radial_noise * amplitude
        dy = self.base_y * radial_noise * amplitude
        dz = self.base_z * radial_noise * amplitude

        tangential_mix = max(0.0, min(1.0, cfg.plexus_crumple_tangential_mix))
        if tangential_mix > 0.0:
            tan_x = fbm3(pos, octaves=octaves, seed=self._seed_offset + 7)
            tan_y = fbm3(pos, octaves=octaves, seed=self._seed_offset + 13)
            tan_z = fbm3(pos, octaves=octaves, seed=self._seed_offset + 19)
            dx += tan_x * amplitude * tangential_mix
            dy += tan_y * amplitude * tangential_mix
            dz += tan_z * amplitude * tangential_mix

        return dx, dy, dz

    def draw(
        self,
        surface,
        t: float,
        audio_level: float,
        audio_bands: tuple[float, float, float] | None = None,
        audio_features: dict | None = None,
    ):
        """Orchestrate the crumple, motion, projection, and edge rendering.

        Args:
            surface: Surface passed to the base-class render path.
            t: Current time in seconds.
            audio_level: Broadband RMS audio level (AudioMeter caps at 1.5).
            audio_bands: (bass, mid, treble) RMS levels; see AudioMeter.
            audio_features: Optional multiband/transient/centroid payload.

        """
        cfg = self.cfg
        if self.node_count < 2 or len(self.edge_i) == 0:
            return

        first_frame = self._last_t is None
        dt = 0.0 if first_frame else min(max(t - self._last_t, 0.0), 0.1)
        self._last_t = t

        audio_level = max(0.0, min(audio_level, 1.5))
        target = max(0.0, audio_level - cfg.audio_noise_threshold)
        # Fast attack, slow release so quiet passages settle gently instead of
        # twitching with every RMS sample.
        rate = 12.0 if target > self._level_env else 1.8
        self._level_env += (target - self._level_env) * (1.0 - np.exp(-rate * dt))
        if first_frame:
            self._level_env = target
        eff_level = self._level_env
        bass, mid, treble = self._resolve_bass_mid_treble(audio_bands, audio_features)
        transient = 0.0
        if audio_features is not None:
            transient = float(audio_features.get("transient", 0.0))

        # Smoothed envelopes: flash decays exponentially but re-triggers
        # instantly on a new onset; swirl/jitter track their band gently.
        self._flash_env = max(
            self._flash_env * cfg.plexus_transient_flash_decay,
            transient * cfg.plexus_transient_flash_strength,
        )
        self._swirl_env = 0.88 * self._swirl_env + 0.12 * mid
        self._jitter_env = 0.90 * self._jitter_env + 0.10 * treble

        # --- shape: noise-driven crumple (+ audio) ---
        crumple_amp = (
            cfg.plexus_crumple_amplitude + cfg.plexus_audio_crumple_boost * eff_level
        )
        dx, dy, dz = self._compute_crumple_displacement(t, crumple_amp)

        if self._jitter_env > 0.0:
            # Scaled down (x0.1) so treble jitter reads as fine shimmer rather
            # than dominating the overall crumpled silhouette.
            jitter = cfg.plexus_treble_jitter_influence * self._jitter_env * 0.1
            dx += jitter * np.sin(self.phase * 5.3 + t * 12.0)
            dy += jitter * np.sin(self.phase * 6.1 + t * 10.0)
            dz += jitter * np.sin(self.phase * 6.9 + t * 14.0)

        x = self.base_x * cfg.plexus_base_radius + dx
        y = self.base_y * cfg.plexus_base_radius + dy
        z = self.base_z * cfg.plexus_base_radius + dz

        # --- whole-mesh breathing (scale pulse), bass-boosted ---
        breathe = 1.0 + cfg.plexus_breath_amplitude * np.sin(
            t * cfg.plexus_breath_speed * 2.0 * np.pi
        )
        breathe += cfg.plexus_bass_scale_influence * bass
        x, y, z = x * breathe, y * breathe, z * breathe

        # --- whole-mesh rotation: audio-boosted speed, precession wobble,
        #     and a mid-driven twist offset on the Z axis ---
        # Angles are integrated so audio-driven speed changes never make the
        # mesh jump.
        rot_boost = 1.0 + cfg.plexus_audio_rotation_boost * eff_level
        self._rot += dt * rot_boost * np.array(
            [
                cfg.plexus_rotation_speed_x,
                cfg.plexus_rotation_speed_y,
                cfg.plexus_rotation_speed_z,
            ]
        )
        wobble = cfg.plexus_precession_wobble * np.sin(t * 0.17)
        rot_x = self._rot[0]
        rot_y = self._rot[1] + wobble
        rot_z = self._rot[2] + cfg.plexus_mid_swirl_influence * self._swirl_env

        cos_y, sin_y = np.cos(rot_y), np.sin(rot_y)
        cos_x, sin_x = np.cos(rot_x), np.sin(rot_x)
        cos_z, sin_z = np.cos(rot_z), np.sin(rot_z)

        x1 = cos_y * x + sin_y * z
        z1 = -sin_y * x + cos_y * z

        y2 = cos_x * y - sin_x * z1
        z2 = sin_x * y + cos_x * z1

        x3 = cos_z * x1 - sin_z * y2
        y3 = sin_z * x1 + cos_z * y2

        # --- project + brightness (depth + audio glow + onset flash) ---
        xs, ys, scale = self._project_to_screen(x3, y3, z2)
        floor = cfg.plexus_min_brightness
        brightness = floor + (1.0 - floor) * self._compute_brightness(scale)
        audio_glow = cfg.plexus_audio_brightness_boost * eff_level + self._flash_env
        brightness = np.clip(brightness + audio_glow, 0.0, 1.0)

        # --- dynamic edge visibility: audio controls how dense the web looks ---
        ei, ej = self.edge_i, self.edge_j
        edge_len = np.sqrt(
            (x3[ei] - x3[ej]) ** 2 + (y3[ei] - y3[ej]) ** 2 + (z2[ei] - z2[ej]) ** 2
        )
        threshold = self._mean_edge_length * (
            cfg.plexus_connection_distance_factor
            + cfg.plexus_connection_distance_audio_boost * (eff_level + self._flash_env)
        )
        threshold = max(threshold, 1e-6)
        # Soft threshold: edges fade in/out over a band instead of popping.
        fade = np.clip((threshold - edge_len) / (0.25 * threshold), 0.0, 1.0)
        fade = fade * fade * (3.0 - 2.0 * fade)
        active = fade > 0.01
        if not np.any(active):
            return

        ai, aj = ei[active], ej[active]
        len_ratio = np.minimum(edge_len[active] / threshold, 1.0)
        falloff = np.clip(1.0 - cfg.plexus_edge_length_falloff * len_ratio, 0.05, 1.0)
        falloff = falloff * fade[active]

        self._render_lines(
            surface,
            xs[ai], ys[ai], xs[aj], ys[aj],
            brightness[ai] * falloff, brightness[aj] * falloff,
            width=cfg.plexus_edge_width,
            alpha=cfg.plexus_edge_base_alpha,
        )

        if cfg.plexus_node_point_size > 0.0:
            node_boost = cfg.plexus_node_brightness_boost
            node_brightness = np.clip(brightness + node_boost, 0.0, 1.0)
            point_size = cfg.plexus_node_point_size
            sizes = np.full(self.node_count, point_size, dtype=np.float64)
            self._render_points(surface, xs, ys, node_brightness, sizes)
