"""Command-line entry point for particled."""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version


def _package_version() -> str:
    """Return installed package version, falling back for source runs."""
    try:
        return version("particled")
    except PackageNotFoundError:
        return "0.0.0+local"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="particled",
        description="Audio-reactive particle visualizer",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"particled {_package_version()}",
    )
    parser.add_argument(
        "-s",
        "--selective",
        action="store_true",
        help="Interactively select style and configure parameters before starting",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the particled application entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Import heavyweight rendering/audio modules only when actually running.
    from particled.runtime import main as run_main

    run_main_args = []
    if args.selective:
        run_main_args.append("--selective")

    # The runtime parser reads sys.argv, so patch it for subprocess-free handoff.
    import sys

    old_argv = sys.argv
    try:
        sys.argv = [old_argv[0], *run_main_args]
        run_main()
    finally:
        sys.argv = old_argv
    return 0
