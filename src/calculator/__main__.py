"""Entry point for ``python -m calculator``.

Configures logging from ``CALCULATOR_LOG_LEVEL`` and starts the GUI.
"""

from __future__ import annotations

import logging
import os
import sys


def configure_logging() -> None:
    """Set up root logging using ``CALCULATOR_LOG_LEVEL`` (default ``WARNING``)."""
    requested = (os.environ.get("CALCULATOR_LOG_LEVEL") or "WARNING").upper()
    level = getattr(logging, requested, None)
    if not isinstance(level, int):
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    if requested not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}:
        logging.getLogger(__name__).warning(
            "Unknown CALCULATOR_LOG_LEVEL=%r; using WARNING", requested
        )


def main() -> int:
    """Start the application and return a process exit code."""
    configure_logging()
    # Absolute import so this module also works as the PyInstaller entry script,
    # where it runs as a top-level script rather than as part of the package.
    from calculator.app import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
