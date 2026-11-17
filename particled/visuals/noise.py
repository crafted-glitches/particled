"""Deterministic, vectorised 3-D value noise (fractal Brownian motion).

Pure NumPy implementation so organic, continuously evolving displacement can be
added to mesh-based visualizations (e.g. Plexus) without a third-party noise
dependency. Not cryptographic — only used for visually pleasing, reproducible
pseudo-random spatial fields.
"""

import numpy as np

_PRIME_X = 374761393
_PRIME_Y = 668265263
_PRIME_Z = 2147483647
_PRIME_SEED = 2246822519
_MASK32 = 0xFFFFFFFF


def _hash3(ix: np.ndarray, iy: np.ndarray, iz: np.ndarray, seed: int) -> np.ndarray:
    """Vectorised integer hash of lattice coordinates to floats in [0, 1)."""
    h = (ix * _PRIME_X) ^ (iy * _PRIME_Y) ^ (iz * _PRIME_Z) ^ (int(seed) * _PRIME_SEED)
    h = h & _MASK32
    h = (h ^ (h >> 13)) * 1274126177 & _MASK32
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(0xFFFFFF)


def _fade(t: np.ndarray) -> np.ndarray:
    """Perlin's quintic ease curve: smooth 1st/2nd derivatives at lattice edges."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def value_noise3(pos: np.ndarray, seed: int = 0) -> np.ndarray:
    """Return smoothed value noise in [-1, 1] for an (N, 3) array of positions.

    Args:
        pos: Array of shape (N, 3) giving the sample coordinates.
        seed: Integer seed selecting an independent noise field.

    Returns:
        Array of shape (N,) with noise values in [-1, 1].

    """
    x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    z0 = np.floor(z).astype(np.int64)
    fx, fy, fz = x - x0, y - y0, z - z0
    ux, uy, uz = _fade(fx), _fade(fy), _fade(fz)

    def corner(dx: int, dy: int, dz: int) -> np.ndarray:
        return _hash3(x0 + dx, y0 + dy, z0 + dz, seed)

    c000, c100 = corner(0, 0, 0), corner(1, 0, 0)
    c010, c110 = corner(0, 1, 0), corner(1, 1, 0)
    c001, c101 = corner(0, 0, 1), corner(1, 0, 1)
    c011, c111 = corner(0, 1, 1), corner(1, 1, 1)

    x00 = c000 + ux * (c100 - c000)
    x10 = c010 + ux * (c110 - c010)
    x01 = c001 + ux * (c101 - c001)
    x11 = c011 + ux * (c111 - c011)

    y0_ = x00 + uy * (x10 - x00)
    y1_ = x01 + uy * (x11 - x01)

    v = y0_ + uz * (y1_ - y0_)
    return (v * 2.0) - 1.0


def fbm3(
    pos: np.ndarray,
    octaves: int = 3,
    seed: int = 0,
    lacunarity: float = 2.0,
    gain: float = 0.5,
) -> np.ndarray:
    """Fractal Brownian motion: layered octaves of :func:`value_noise3`.

    Args:
        pos: Array of shape (N, 3) giving the sample coordinates.
        octaves: Number of noise layers to sum (more = finer surface detail).
        seed: Base integer seed; each octave uses a distinct derived seed.
        lacunarity: Frequency multiplier applied between successive octaves.
        gain: Amplitude multiplier applied between successive octaves.

    Returns:
        Array of shape (N,) with normalised noise values in [-1, 1].

    """
    total = np.zeros(pos.shape[0], dtype=np.float64)
    amplitude = 1.0
    frequency = 1.0
    norm = 0.0
    for i in range(max(1, int(octaves))):
        total += amplitude * value_noise3(pos * frequency, seed=seed + i * 101)
        norm += amplitude
        amplitude *= gain
        frequency *= lacunarity
    return total / max(norm, 1e-8)
