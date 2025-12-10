"""Particled - Audio Reactive Particle Visualizer."""

import os

# Suppress pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from particled.audio import AudioMeter
from particled.config import Config
from particled.visuals import (
    BaseVisualization,
    ParticleCloudGravitas,
    ParticleCloudImpact,
    TorusKnotField,
)

__all__ = [
    "AudioMeter",
    "BaseVisualization",
    "Config",
    "ParticleCloudGravitas",
    "ParticleCloudImpact",
    "TorusKnotField",
]
