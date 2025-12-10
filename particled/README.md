# Particled Package Structure

This package contains the audio-reactive particle visualizer, now organized into modular components with multiple visualization styles.

## Directory Structure

```
particled/
├── __init__.py              # Package initialization, exports main classes
├── config.py                # Configuration dataclass
├── audio.py                 # Audio input processing (AudioMeter)
├── cli.py                   # Interactive CLI configuration
└── visuals/                 # Visualization modules
    ├── __init__.py          # Visuals package exports
    ├── base.py              # Base visualization utilities and abstract class
    ├── particle_cloud/      # Particle Cloud modes
    │   ├── __init__.py      # Particle Cloud exports
    │   ├── base.py          # Shared Particle Cloud functionality
    │   ├── impact.py        # Impact mode (breathing animation)
    │   └── gravitas.py      # Gravitas mode (physics-based expansion)
    └── torus_knot.py        # Torus Knot visualization

../main.py                   # Application entry point
```

## Modules

### `config.py`
Contains the `Config` dataclass with all visualization parameters:
- Window settings
- Particle geometry parameters
- Motion and rotation settings
- Audio reactivity settings
- Visual style settings
- Audio input settings
- Particle Cloud specific parameters
- Gravitas mode specific parameters (push strength, return mechanics, frequency bands)
- Torus Knot specific parameters

### `audio.py`
Contains the `AudioMeter` class for real-time audio input processing:
- Background microphone monitoring
- RMS level calculation
- Smoothed audio level output

### `visuals/base.py`
Contains the base visualization infrastructure:
- `BaseVisualization`: Abstract base class for all visualizations
  - `_project_to_screen()`: Shared 3D to 2D projection with FOV
  - `_compute_brightness()`: Gamma-corrected brightness calculation
  - `_render_points()`: Shared pygame rendering logic
  - `draw()`: Abstract method for visualization implementations
- `fade_surface()`: Motion trail effect utility

### `visuals/torus_knot.py`
Contains the `TorusKnotField` visualization:
- Complex mathematical knot patterns
- Methods:
  - `_compute_torus_knot_positions()`: Base 3D torus-knot geometry
  - `_apply_distortion()`: Audio-driven wobble effects
  - `_rotate_3d()`: 3D rotations around X and Y axes
  - `_compute_sizes()`: Brightness-based particle sizing
  - `draw()`: Main orchestration method

### `visuals/particle_cloud/`
Package containing Particle Cloud visualization modes with shared base functionality.

#### `visuals/particle_cloud/base.py`
Contains `ParticleCloudBase` - shared functionality for all Particle Cloud modes:
- Gaussian spherical particle distribution
- Phase offset generation for drift animations
- Density weight calculation
- Common rotation and sizing methods
- Methods:
  - `_initialize_base_particles()`: Creates base spherical distribution
  - `_apply_rotation()`: Rotation around X and Y axes
  - `_compute_sizes()`: Density-based particle sizing

#### `visuals/particle_cloud/impact.py`
Contains `ParticleCloudImpact` visualization:
- Dense particle cloud with soft, nebula-like density gradient
- Whole-cloud breathing animation with audio reactivity
- Pure white particles on black background
- Methods:
  - `_apply_gentle_motion()`: Drift and breathing animation
  - `_compute_sizes_with_audio()`: Audio-reactive particle sizing
  - `draw()`: Main orchestration method

#### `visuals/particle_cloud/gravitas.py`
Contains `ParticleCloudGravitas` visualization:
- Gravity-centered particle cloud with outward expansion on audio impact
- Three configurable return mechanics (spring/linear/exponential)
- Frequency-based particle mapping (bass/mid/treble)
- Idle behavior with drift and rotation only (no breathing)
- Audio noise threshold to prevent ambient sound jitter
- Methods:
  - `_initialize_particles()`: Spherical cloud with displacement tracking
  - `_apply_audio_push()`: Radial push from center based on audio
  - `_apply_return_mechanic()`: Return-to-center physics
  - `_apply_spring_return()`: Spring oscillation mechanics
  - `_apply_linear_return()`: Linear damped return
  - `_apply_exponential_return()`: Exponential decay return
  - `_apply_idle_motion()`: Gentle drift without breathing
  - `draw()`: Main orchestration method

### `cli.py`
Contains interactive configuration functions:
- `get_visualization_style()`: Select between visualization styles
- `get_particle_cloud_mode()`: Select between Gravitas and Impact modes
- `configure_gravitas()`: Gravitas mode specific configuration
- `configure_impact()`: Impact mode specific configuration
- `configure_torus_knot()`: Torus Knot specific configuration
- `configure_interactively()`: Routes to style and mode-specific configuration
- `prompt_for_interactive_config()`: Ask user for interactive mode

### `../main.py`
Application entry point that:
- Prompts user to select visualization style ("Torus Knot" or "Particle Cloud")
- For Particle Cloud, prompts to select mode ("Gravitas" or "Impact")
- Prompts for interactive or default configuration
- Initializes pygame window with resizable support
- Sets up the selected visualization and audio meter
- Runs the main event loop with keyboard (ESC) and window controls
- Handles window resize events dynamically
- Displays mode name in window caption if applicable

## Usage

### Running the Application

Execute the visualizer from the command line:

```bash
# From the project root directory
python main.py
```

Or using poetry:

```bash
poetry run python main.py
```

The application will prompt you to:
1. **Select visualization style**: Choose between "Torus Knot" (complex mathematical patterns) or "Particle Cloud" (nebula-like density gradient)
2. **Select Particle Cloud mode** (if applicable): Choose between "Gravitas" (physics-based expansion) or "Impact" (breathing animation)
3. **Configure parameters**: Optionally customize parameters interactively

### Visualization Styles

#### Torus Knot
Complex mathematical knot patterns with intricate 3D geometry. Features:
- Dynamic torus-knot mathematics
- Audio-driven distortion and rotation
- Configurable knot complexity (μ and ν parameters)

#### Particle Cloud
Minimal, nebula-like particle cloud with soft density gradients. Two distinct modes:

##### Gravitas Mode (Default)
Gravity-centered particle physics with audio-reactive expansion:
- **Audio Reactivity**: Particles push radially outward from center on audio impact
- **Audio Threshold**: Configurable noise baseline (default: 0.05) prevents ambient jitter
- **Return Mechanics**: Three configurable physics models:
  - **Exponential** (default): Fast-then-slow natural decay (organic feel)
  - **Spring**: Bouncy oscillation with overshoot (lively, dynamic)
  - **Linear**: Constant-speed damped return (predictable, smooth)
- **Frequency Mapping**: Particles respond based on radial distance:
  - Bass band (0.0-0.3): Outer particles, 70% base + 30% audio response
  - Mid band (0.3-0.7): Middle particles, 100% audio response
  - Treble band (0.7-1.0): Inner particles, 50% base + 50% audio response
- **Idle Motion**: Gentle drift and rotation only (no breathing)

##### Impact Mode
Whole-cloud breathing animation with soft expansion:
- Gaussian spherical distribution for natural density falloff
- Gentle breathing and drift animations
- Audio-reactive size and motion with configurable boost
- Pure white particles on black background for a clean aesthetic

### Using as a Library

```python
from particled import (
    AudioMeter,
    Config,
    ParticleCloudGravitas,
    ParticleCloudImpact,
    TorusKnotField,
)
from particled.cli import configure_interactively, prompt_for_interactive_config
from particled.visuals import fade_surface

# Use default configuration
config = Config()

# Or use interactive configuration with style-specific parameters
style = "Particle Cloud"  # or "Torus Knot"
config, mode = configure_interactively(style)  # Returns (config, mode)

# Create a visualization
torus_field = TorusKnotField(config)
# or
gravitas_cloud = ParticleCloudGravitas(config)
# or
impact_cloud = ParticleCloudImpact(config)

# Programmatic Gravitas configuration example
config = Config()
config.audio_noise_threshold = 0.05
config.gravitas_push_strength = 2.0
config.gravitas_return_mechanic = "exponential"
config.gravitas_exponential_decay_rate = 0.15

# For spring mechanic:
# config.gravitas_return_mechanic = "spring"
# config.gravitas_spring_strength = 0.5
# config.gravitas_spring_damping = 0.8
# config.gravitas_spring_mass = 1.0

# Initialize components
field = ParticleCloudGravitas(config)
audio_meter = AudioMeter(config)
```

## Interactive Configuration Parameters

When running with interactive configuration, you can customize parameters specific to your selected visualization style.

### Common Parameters (Both Styles)

#### Number of Particles (100-20000, default: 5500)
Controls the density and detail of the visualization.
- **Lower values (100-1000)**: Sparse, minimal particle field with visible individual points. Faster performance on slower systems.
- **Medium values (2000-8000)**: Balanced density with good visual detail and smooth appearance.
- **Higher values (10000-20000)**: Dense, cloud-like appearance with rich detail. May impact performance.

#### Audio Reactivity Gain (0.0-200.0, default: 50.0)
Amplifies the microphone input's effect on the visualization.
- **0.0**: No audio reaction - visualization is purely time-based animation.
- **10-30**: Subtle audio response, gentle pulsing with loud sounds.
- **40-70**: Moderate response, clear visual reaction to music and speech.
- **80-120**: Strong response, dramatic changes with audio input.
- **120-200**: Extreme sensitivity, even quiet sounds cause major visual shifts.
- **Note**: Higher values may cause clipping; adjust based on your environment's noise level.

#### Trail Fade Alpha (0-255, default: 25)
Controls how quickly particle trails fade, creating motion blur effects.
- **0**: No fading - particles leave permanent trails, creating a persistent drawing effect. Screen gradually fills with white.
- **1-10**: Very slow fade - long, flowing trails that persist for seconds. Dreamy, ethereal appearance.
- **15-40**: Medium fade - balanced trails that show recent motion paths clearly.
- **50-100**: Fast fade - short trails, snappy motion with minimal blur.
- **150-254**: Very fast fade - almost no trails, sharp particle positions.
- **255**: Instant clear - no trails at all, particles disappear immediately. Cleanest, most precise look.

#### Brightness Gamma (0.5-3.0, default: 1.8)
Adjusts the contrast and brightness distribution using gamma correction.
- **0.5-1.0**: Lower gamma - more even brightness, brings out dimmer particles. Flatter, more uniform appearance.
- **1.0-1.5**: Balanced - natural brightness distribution with good depth perception.
- **1.5-2.2**: Enhanced contrast - brighter highlights, darker shadows. More dramatic, punchy look (default: 1.8).
- **2.2-3.0**: High contrast - extreme brightness variation. Very bright centers fade quickly to dark edges.

### Particle Cloud Specific Parameters

Parameters shared across both Impact and Gravitas modes:

#### Density Sigma (0.1-5.0, default: 1.0)
Controls the Gaussian distribution spread of particles (affects density gradient).
- **0.1-0.5**: Very tight cluster - extremely dense center with sharp falloff. Compact, star-like core.
- **0.5-1.5**: Moderate spread - soft nebula-like gradient with natural density falloff (default: 1.0).
- **1.5-3.0**: Wide spread - more diffuse cloud with gentle gradient. Expansive, ethereal appearance.
- **3.0-5.0**: Very diffuse - particles spread far from center. Sparse, galaxy-like distribution.

#### Drift Speed (0.0-1.0, default: 0.1)
Speed of the gentle, organic drift motion.
- **0.0**: No drift - particles maintain their base positions.
- **0.05-0.15**: Slow, subtle drift - barely perceptible organic movement (default: 0.1).
- **0.2-0.4**: Medium drift - noticeable floating, cloud-like motion.
- **0.5-1.0**: Fast drift - active swirling and flowing movement.

#### Rotation Speed Y-axis (0.0-0.5, default: 0.05)
Horizontal rotation speed around the Y-axis.
- **0.0**: No rotation - cloud maintains orientation.
- **0.01-0.08**: Very slow rotation - subtle spatial awareness (default: 0.05).
- **0.1-0.2**: Gentle rotation - noticeable but still calm.
- **0.2-0.5**: Moderate rotation - more dynamic view of the cloud structure.

#### Rotation Speed X-axis (0.0-0.5, default: 0.03)
Vertical rotation speed around the X-axis.
- **0.0**: No vertical rotation.
- **0.01-0.05**: Subtle tumbling motion (default: 0.03).
- **0.05-0.15**: Gentle vertical rotation.
- **0.15-0.5**: More active vertical tumbling.

### Impact Mode Specific Parameters

#### Breathing Speed (0.0-2.0, default: 0.3)
Speed of the expansion/contraction breathing animation.
- **0.0**: No breathing - cloud maintains constant size.
- **0.1-0.4**: Slow breathing - gentle, meditative pulsing (default: 0.3).
- **0.5-1.0**: Medium breathing - noticeable rhythmic expansion/contraction.
- **1.0-2.0**: Fast breathing - rapid pulsing, energetic feel.

### Gravitas Mode Specific Parameters

#### Audio Noise Threshold (0.0-0.5, default: 0.05)
Baseline noise level to ignore, preventing jitter from ambient sound.
- **0.0**: No threshold - all audio input affects particles (may be jittery).
- **0.02-0.08**: Low threshold - filters quiet ambient noise (default: 0.05).
- **0.1-0.2**: Medium threshold - requires moderate sound for reaction.
- **0.3-0.5**: High threshold - only loud sounds trigger particle movement.

#### Audio Push Strength (0.5-10.0, default: 2.0)
Force applied to push particles outward from center on audio impact.
- **0.5-1.5**: Gentle push - subtle expansion with soft audio response.
- **1.5-3.0**: Medium push - balanced, noticeable outward movement (default: 2.0).
- **3.0-5.0**: Strong push - dramatic expansion with audio peaks.
- **5.0-10.0**: Extreme push - explosive particle dispersion.

#### Return Mechanic (exponential/spring/linear, default: exponential)
Physics model for how particles return to their base positions after push.

**Exponential (default)**:
- Fast-then-slow natural decay for organic feel
- **Decay Rate** (0.05-0.5, default: 0.15): Controls return speed
  - Lower values = slower, longer-lasting expansion
  - Higher values = faster return to center

**Spring**:
- Bouncy oscillation with overshoot for lively, dynamic movement
- **Spring Strength** (0.1-2.0, default: 0.5): Force pulling back to center
- **Spring Damping** (0.1-1.0, default: 0.8): Reduces oscillation amplitude
- **Spring Mass** (0.1-5.0, default: 1.0): Inertia of particles

**Linear**:
- Constant-speed damped return for predictable, smooth motion
- **Return Speed** (0.1-1.0, default: 0.3): Speed of return movement
- **Damping Factor** (0.5-1.0, default: 0.9): Gradual slowdown rate

### Torus Knot Specific Parameters

#### Torus Knot Parameter μ (mu) (1-10, default: 2)
Defines how many times the knot loops around the torus longitudinally.
- **μ = 1**: Simple ring/circle shape.
- **μ = 2**: Figure-eight pattern with two loops.
- **μ = 3-5**: Increasingly complex braided patterns.
- **μ = 6-10**: Very intricate, highly detailed knot structures.
- **Note**: The relationship between μ and ν creates the knot's unique topology.

#### Torus Knot Parameter ν (nu) (1-10, default: 3)
Defines how many times the knot loops around the torus meridionally.
- **ν = 1**: Minimal vertical complexity.
- **ν = 2-3**: Classic trefoil and cinquefoil knot appearances.
- **ν = 4-6**: Complex interweaving patterns with multiple crossings.
- **ν = 7-10**: Extremely intricate structures with many overlapping paths.
- **Tip**: Try (μ=2, ν=3), (μ=3, ν=2), (μ=3, ν=5), or (μ=5, ν=7) for beautiful patterns.

#### Base Rotation Speed Y-axis (0.0-2.0, default: 0.25)
Controls horizontal (left-right) rotation speed of the entire structure.
- **0.0**: No horizontal rotation - structure appears stationary side-to-side.
- **0.1-0.5**: Slow, graceful rotation good for observation and screenshots.
- **0.5-1.0**: Medium speed rotation providing good spatial awareness.
- **1.0-2.0**: Fast rotation that emphasizes the 3D nature and creates motion blur effects.
- **Negative values**: Reverses rotation direction.

#### Base Rotation Speed X-axis (0.0-2.0, default: 0.13)
Controls vertical (up-down) rotation speed of the entire structure.
- **0.0**: No vertical rotation - structure maintains fixed vertical orientation.
- **0.1-0.3**: Subtle tumbling motion that reveals vertical complexity.
- **0.3-0.8**: Noticeable tumbling that shows all angles of the structure.
- **0.8-2.0**: Rapid spinning that creates dynamic, ever-changing views.
- **Tip**: Different X and Y speeds create complex Lissajous-like rotation patterns.

### Brightness Gamma (0.5-3.0, default: 1.8)
Adjusts the contrast and brightness distribution based on particle depth.
- **0.5-0.9**: Low contrast - particles at all depths appear similarly bright, flat appearance.
- **1.0**: Linear brightness - natural depth perception without enhancement.
- **1.2-1.8**: Medium enhancement - good depth perception with brighter foreground.
- **1.9-2.5**: High contrast - dramatic depth, distant particles very dim, close ones very bright.
- **2.6-3.0**: Extreme contrast - only nearest particles visible, creates sharp focus effect.
- **Effect**: Higher values make the structure appear more three-dimensional with dramatic lighting.
