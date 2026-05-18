"""Logging configuration for oar-rmm-python.

Call ``setup_logging()`` once during application startup (done in app/main.py).

If the ``LOGGING_CONFIG_FILE`` environment variable points to a JSON file, that
file is loaded directly with ``logging.config.dictConfig()``.  The file must
be a valid Python logging dictConfig mapping:
https://docs.python.org/3/library/logging.config.html#logging-config-dictschema

When ``LOGGING_CONFIG_FILE`` is not set (local development), a basic stderr
handler is configured as a fallback.

The log level can be set with the ``LOG_LEVEL`` environment variable.
"""

import json
import logging
import logging.config
import os
from typing import Optional


def setup_logging(log_level: Optional[str] = None) -> None:
    """Configure application logging.

    If the ``LOGGING_CONFIG_FILE`` environment variable points to an existing
    file, that file is loaded directly with ``logging.config.dictConfig()``.
    The file must be a JSON-serialised dictConfig mapping.

    Falls back to a stderr handler when no config file is provided.

    The level can be overridden with the ``LOG_LEVEL`` env var.
    """
    level = (log_level or os.environ.get("LOG_LEVEL", "info")).upper()

    config_file = os.environ.get("LOGGING_CONFIG_FILE")
    if config_file and os.path.isfile(config_file):
        try:
            with open(config_file) as fh:
                logging.config.dictConfig(json.load(fh))
            logging.getLogger(__name__).info(
                "Logging configured from %s", config_file
            )
            return
        except Exception as exc:
            logging.warning(
                "Could not load %s: %s — falling back to stderr", config_file, exc
            )

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=__import__("sys").stderr,
    )
    logging.getLogger(__name__).info(
        "Logging configured | level=%s destination=stderr", level
    )
