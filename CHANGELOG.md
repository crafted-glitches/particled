# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

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
