#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
python -m pip install build twine

rm -rf dist
python -m build
python -m twine check dist/*

shasum -a 256 dist/* | tee dist/SHA256SUMS.txt

echo "Artifacts prepared in dist/"
