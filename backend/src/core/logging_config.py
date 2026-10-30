"""Module: logging_config.py

Purpose:
Configures structured application logging for the FastAPI backend service.

Responsibilities:
- Initialize Python's standard logging system with consistent formatting.
- Format log records with timestamp, level, module name, and message.
- Provide a clean logger instance for application tracing.
"""

import logging
import sys


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the root application logger.

    Args:
        level:
            Logging level (default: logging.INFO).

    Returns:
        Configured logging.Logger instance.
    """
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger("restoration_studio")
    logger.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if not logger.handlers:
        logger.addHandler(handler)

    return logger

