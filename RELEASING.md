# Releasing Particled

## Versioning policy
- Semantic Versioning is used: MAJOR.MINOR.PATCH.
- MAJOR: incompatible public behavior changes.
- MINOR: backward-compatible features.
- PATCH: backward-compatible fixes.

## Release checklist
- Ensure main is green in CI (lint, tests, typecheck, build).
- Update CHANGELOG.md under Unreleased and cut a version section.
- Bump version in pyproject.toml.
- Commit release metadata and tag:
  - git tag vX.Y.Z
  - git push origin vX.Y.Z
- Build artifacts locally (optional preflight):
  - python -m build
  - twine check dist/*
- Publish via GitHub release workflow using trusted publishing.

## Migration notes policy
- Any backward-incompatible or operationally significant change must include:
  - A "Migration" note in CHANGELOG.md.
  - A short upgrade snippet in README.md if user action is required.
