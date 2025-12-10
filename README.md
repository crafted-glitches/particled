# Particled

Audio-reactive particle visualizer with multiple visualization styles and modes.

## Overview

Particled is a real-time particle visualization system that responds to microphone input, featuring:

- **Torus Knot**: Complex mathematical knot patterns with 3D geometry
- **Particle Cloud - Gravitas Mode**: Physics-based gravity-centered expansion with audio reactivity
- **Particle Cloud - Impact Mode**: Whole-cloud breathing animation with gentle drift
- **Penrose Triangle**: Impossible triangle geometry with audio-reactive particle flow

## Features

- Real-time audio reactivity via microphone input
- Multiple visualization styles and sub-modes
- Interactive CLI configuration
- Resizable window with fullscreen support
- Configurable particle physics and return mechanics
- Frequency-based particle mapping (Gravitas mode)
- Adjustable motion trails and visual effects

## Installation

Requires Python 3.14+ and Poetry.

```bash
# Clone the repository
git clone https://github.com/crafted-glitches/particled.git
cd particled

# Install dependencies
poetry install
```

## Quick Start

```bash
# Run with interactive configuration
poetry run python main.py

# Or run directly with Python
python main.py
```

The application will prompt you to:
1. Select visualization style (Torus Knot or Particle Cloud)
2. Select mode (for Particle Cloud: Gravitas or Impact)
3. Optionally configure parameters interactively

**Controls:**
- `ESC` - Exit the application
- Window is resizable by default

## Visualization Modes

### Torus Knot
Complex mathematical patterns based on torus knot geometry with audio-driven distortion and rotation.

### Particle Cloud - Gravitas (Default)
Physics-based particle system where audio pushes particles radially outward from center:
- Audio threshold to prevent ambient noise jitter
- Three return mechanics: Exponential (default), Spring, or Linear
- Frequency-band particle mapping (bass/mid/treble)
- Drift and rotation when idle

### Particle Cloud - Impact
Gentle whole-cloud breathing animation with:
- Soft expansion and contraction
- Drift motion for organic feel
- Audio-reactive size and motion

## Documentation

See [particled/README.md](particled/README.md) for comprehensive documentation including:
- Package structure and module details
- Complete parameter reference
- Configuration examples
- API usage guide

## Configuration

All parameters can be configured either:
- **Interactively** via CLI prompts at startup
- **Programmatically** via the `Config` dataclass

Example programmatic configuration:

```python
from particled import Config, ParticleCloudGravitas

cfg = Config()
cfg.num_particles = 8000
cfg.audio_noise_threshold = 0.05
cfg.gravitas_push_strength = 2.5
cfg.gravitas_return_mechanic = "spring"

field = ParticleCloudGravitas(cfg)
```

## Development

```bash
# Install development dependencies
poetry install --with dev

# Run linter
poetry run ruff check .

# Run tests
poetry run pytest

# Install pre-commit hooks
poetry run pre-commit install
```

## License

[Add your license here]

## Credits

Built with:
- [Pygame](https://www.pygame.org/) - Graphics and window management
- [NumPy](https://numpy.org/) - Numerical computations
- [sounddevice](https://python-sounddevice.readthedocs.io/) - Audio input
- [InquirerPy](https://inquirerpy.readthedocs.io/) - Interactive CLI
