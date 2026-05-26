"""Compatibility wrapper to run particled from repository root.

Use `particled` or `python -m particled` for installed usage.
"""

from particled.runtime import main


if __name__ == "__main__":
    main()
