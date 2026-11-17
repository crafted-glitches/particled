# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

## [0.10.0] - 2026-11-17

### Added
- New **Plexus** visualization style: a crumpled, audio-reactive wireframe mesh of nodes on a Fibonacci sphere lattice, connected by a dense web of nearest-neighbor and long-range "chord" edges whose visibility, brightness, and crumple intensity react to audio level, frequency bands, and onsets.
- GPU line-segment rendering (`GLRenderer.render_lines`) and a matching CPU fallback (`BaseVisualization._render_lines`), expanding each edge into an anti-aliased, configurable-width quad independent of driver `glLineWidth` support.
- Dependency-free vectorised 3-D value noise / fractal Brownian motion module (`particled.visuals.noise`) used to drive the Plexus mesh's organic deformation.
- Plexus resting behaviour is now graceful: audio level is smoothed (fast attack, slow release), edges fade in and out over a soft threshold instead of popping, rotation angles are integrated so audio changes never cause jumps, and default motion is calmer.
- Plexus is brighter by default (near-white edges) with a new `plexus_min_brightness` floor, higher edge opacity and gentler length falloff.
- Over two dozen new `plexus_*` configuration parameters spanning node/edge topology, noise shape, whole-mesh motion, and per-band audio reactivity, plus matching CLI prompts, live parameter panel sections, and preset support.

## [0.9.1] - 2026-05-26

### Fixed
- `particled` command installed from PyPI no longer crashes with `ModuleNotFoundError: No module named 'main'`.
- Runtime launcher is now package-local (`particled.runtime`) so installed environments do not rely on repository-root files.
- `particled --version` now reports the installed package version dynamically instead of a stale hardcoded value.

## [0.9.0] - 2026-05-26

### Added
- Multi-style visualization runtime with Torus Knot, Penrose Triangle, and Particle Cloud modes (Impact and Gravitas).
- Real-time audio reactivity pipeline with RMS monitoring, multiband FFT analysis, transient/onset signal, and spectral centroid features.
- Runtime parameter overlays with live style/mode switching, reset controls, and interactive tuning.
- Per-band particle controls (8 bands) for independent particle count and particle size mapping.
- Preset save/load support from params panel using JSON persistence under `.0folder.bak/presets`.
- Stable CLI entry points via `particled` and `python -m particled`.
- Release governance assets: `LICENSE` (MIT), `RELEASING.md`, and this changelog.
- CI automation for lint/test/type/build checks across Linux and macOS.
- Trusted publishing workflow for PyPI and Homebrew smoke workflow scaffolding.

### Changed
- Particle limit controls now support up to 20,000 particles in runtime panel ranges.
- Linux-only graphics environment overrides are isolated from macOS behavior.
- Audio-driven particle mapping upgraded to stable per-particle band gating and per-band size modulation.
- Config and defaults expanded for advanced audio analysis and Gravitas behavior controls.

### Fixed
- Homebrew smoke workflow updated to install from a temporary CI tap (compatible with Homebrew tap requirements).
- Linux CI test collection no longer hard-fails on missing PortAudio by removing eager audio import side effects.
- Rendering math hardened in key normalization paths to avoid edge-case max-value issues.
