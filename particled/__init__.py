"""Particled - Audio Reactive Particle Visualizer."""

import os
from importlib import import_module
from typing import TYPE_CHECKING, Any

# Suppress pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

if TYPE_CHECKING:
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


def __getattr__(name: str) -> Any:
    """Lazily resolve public API symbols to avoid heavyweight import side effects."""
    if name == "Config":
        return import_module("particled.config").Config
    if name == "AudioMeter":
        return import_module("particled.audio").AudioMeter
    if name in {
        "BaseVisualization",
        "ParticleCloudGravitas",
        "ParticleCloudImpact",
        "TorusKnotField",
    }:
        return getattr(import_module("particled.visuals"), name)
    raise AttributeError(f"module 'particled' has no attribute {name!r}")
