"""Command-line entry point for particled."""

from __future__ import annotations

import argparse


VERSION = "0.1.0"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="particled",
        description="Audio-reactive particle visualizer",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"particled {VERSION}",
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
    from main import main as run_main

    run_main_args = []
    if args.selective:
        run_main_args.append("--selective")

    # main.py parses sys.argv internally; patch argv-style behavior by reusing
    # subprocess-free invocation through argparse-compatible globals.
    import sys

    old_argv = sys.argv
    try:
        sys.argv = [old_argv[0], *run_main_args]
        run_main()
    finally:
        sys.argv = old_argv
    return 0
