"""Centralised logging configuration for oar-rmm-python.

Log format
----------
File / production (RMMFormatter, colorize=False)::

    2026-05-15 10:23:45.123 | INFO     | app.routers.record            | [a1b2c3d4] | message

Console / development (RMMFormatter, colorize=True):

    Same but with ANSI colour on the level and dim styling on metadata.

Sample session
--------------
::

    2026-05-15 10:23:44.900 | INFO     | app.logging_setup             |            | Logging configured | level=INFO destination=stderr (console)
    2026-05-15 10:23:45.003 | INFO     | app.config                    |            | Using configuration from environment variables
    2026-05-15 10:23:45.100 | INFO     | rmm.http                      | [a1b2c3d4] | → GET /rmm/records?searchphrase=laser
    2026-05-15 10:23:45.123 | INFO     | app.crud.record               | [a1b2c3d4] | Query executed in 21 ms — 8 results
    2026-05-15 10:23:45.145 | INFO     | rmm.http                      | [a1b2c3d4] | ← 200  GET /rmm/records  45ms
    2026-05-15 10:23:46.200 | WARNING  | rmm.http                      | [b2c3d4e5] | ← 200  GET /rmm/records  623ms  ⚠ SLOW
    2026-05-15 10:23:47.010 | ERROR    | app.crud.record               | [c3d4e5f6] | MongoDB query failed
        Traceback (most recent call last):
          File "app/crud/record.py", line 45, in search
            result = collection.find(query_filter)
        pymongo.errors.NetworkTimeout: ...

Request IDs
-----------
RequestLoggingMiddleware (app/middleware/logging_middleware.py) generates a
UUID per request and stores it via ``set_request_id()``.  RMMFormatter reads
it via ``get_request_id()`` automatically, so every log line emitted while
handling that request is tagged with the same short ID.  No code changes are
needed in routers or CRUD modules.

Usage
-----
Call ``setup_logging()`` once, early in the application lifespan (done in
app/main.py).  All other modules just do::

    import logging
    logger = logging.getLogger(__name__)
"""

import json
import logging
import logging.config
import os
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Request-ID context variable
# ---------------------------------------------------------------------------

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the request-id for the current async task / thread."""
    return _request_id_var.get()


def set_request_id(value: str) -> None:
    """Set the request-id for the current async task / thread."""
    _request_id_var.set(value)


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------

_ANSI_RESET = "\033[0m"
_ANSI_DIM   = "\033[2m"
_ANSI_BOLD  = "\033[1m"
_LEVEL_COLOR = {
    "DEBUG":    "\033[36m",    # cyan
    "INFO":     "\033[32m",    # green
    "WARNING":  "\033[33m",    # yellow
    "ERROR":    "\033[31m",    # red
    "CRITICAL": "\033[1;31m",  # bold red
}

_W_LEVEL  = 8   # "CRITICAL" = 8 chars — longest standard level name
_W_LOGGER = 30  # truncate from left so the most-specific segment is visible
_W_REQ    = 10  # "[a1b2c3d4]" = bracket + 8 hex chars + bracket


class RMMFormatter(logging.Formatter):
    """Crisp, fixed-width single-line formatter with optional ANSI colour.

    Column layout::

        <timestamp 23> | <level 8> | <logger 30> | <req_id 10> | <message>

    Tracebacks are indented by 4 spaces on continuation lines so the eye can
    immediately separate the exception block from the next normal log line.

    Designed to be registered through dictConfig's ``()`` factory mechanism::

        "formatters": {
            "rmm":       {"()": "app.logging_setup.RMMFormatter", "colorize": False},
            "rmm_color": {"()": "app.logging_setup.RMMFormatter", "colorize": True},
        }
    """

    def __init__(self, colorize: bool = False) -> None:
        super().__init__()
        self.colorize = colorize

    # ------------------------------------------------------------------

    def _fmt_name(self, name: str) -> str:
        """Left-justify within _W_LOGGER, truncating from the left when needed."""
        if len(name) <= _W_LOGGER:
            return name.ljust(_W_LOGGER)
        # Keep the rightmost (most specific) segment of the dotted path
        return ("\u2026" + name[-(_W_LOGGER - 1):]).ljust(_W_LOGGER)

    def _fmt_req_id(self) -> str:
        rid = get_request_id()
        if rid == "-":
            return " " * _W_REQ
        return f"[{rid[:8]}]"

    # ------------------------------------------------------------------

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:  # noqa: N802
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"

    def format(self, record: logging.LogRecord) -> str:
        ts     = self.formatTime(record)
        level  = record.levelname.ljust(_W_LEVEL)
        name   = self._fmt_name(record.name)
        req_id = self._fmt_req_id()
        msg    = record.getMessage()

        # Build exception / stack text (indented 4 spaces)
        exc_text = ""
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            exc_text = "\n" + "\n".join(
                "    " + ln for ln in record.exc_text.splitlines()
            )
        if record.stack_info:
            stack = self.formatStack(record.stack_info)
            exc_text += "\n" + "\n".join("    " + ln for ln in stack.splitlines())

        if self.colorize:
            color = _LEVEL_COLOR.get(record.levelname, "")
            line = (
                f"{_ANSI_DIM}{ts}{_ANSI_RESET} | "
                f"{color}{_ANSI_BOLD}{level}{_ANSI_RESET} | "
                f"{_ANSI_DIM}{name}{_ANSI_RESET} | "
                f"{_ANSI_DIM}{req_id}{_ANSI_RESET} | "
                f"{msg}"
            )
        else:
            line = f"{ts} | {level} | {name} | {req_id} | {msg}"

        return line + exc_text


# ---------------------------------------------------------------------------
# Config builder
# ---------------------------------------------------------------------------

def build_logging_config(log_level: str = "INFO") -> dict:
    """Return a ``logging.config.dictConfig``-compatible configuration dict.

    Produces a colourised ``StreamHandler`` to stderr.  Used as the fallback
    when no ``LOGGING_CONFIG_FILE`` is provided (local development).

    Uvicorn's built-in per-request access lines are suppressed (set to
    WARNING) because ``RequestLoggingMiddleware`` emits richer ones.
    """
    formatters = {
        "rmm_color": {
            "()": "app.logging_setup.RMMFormatter",
            "colorize": True,
        },
    }

    handlers: dict = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "rmm_color",
            "stream": "ext://sys.stderr",
        }
    }
    root_handlers = ["console"]
    access_handlers = ["console"]

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "root": {
            "level": log_level,
            "handlers": root_handlers,
        },
        "loggers": {
            # Route uvicorn through the same destination as the app
            "uvicorn": {
                "level": log_level,
                "handlers": root_handlers,
                "propagate": False,
            },
            # Suppress uvicorn's own per-request lines; RequestLoggingMiddleware
            # emits richer ones.  Keep WARNINGS+ (e.g. client disconnects).
            "uvicorn.access": {
                "level": "WARNING",
                "handlers": access_handlers,
                "propagate": False,
            },
            "uvicorn.error": {
                "level": log_level,
                "handlers": root_handlers,
                "propagate": False,
            },
            "gunicorn.error": {
                "level": log_level,
                "handlers": root_handlers,
                "propagate": False,
            },
            "gunicorn.access": {
                "level": log_level,
                "handlers": access_handlers,
                "propagate": False,
            },
            # Our request logger → access log (separate file when available)
            "rmm.http": {
                "level": log_level,
                "handlers": access_handlers,
                "propagate": False,
            },
        },
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def setup_logging(log_level: Optional[str] = None) -> None:
    """Configure application logging.

    If the ``LOGGING_CONFIG_FILE`` environment variable points to an existing
    file, that file is loaded directly with ``logging.config.dictConfig()``.
    The file must be a JSON-serialised dictConfig mapping
    (see https://docs.python.org/3/library/logging.config.html#logging-config-dictschema).

    When no config file is provided (local development) a colourised stderr
    handler is used instead.

    The level can be overridden with the ``LOG_LEVEL`` env var.
    """
    level = (log_level or os.environ.get("LOG_LEVEL", "info")).upper()

    config_file = os.environ.get("LOGGING_CONFIG_FILE")
    if config_file and os.path.isfile(config_file):
        try:
            with open(config_file) as fh:
                logging.config.dictConfig(json.load(fh))
            logging.getLogger(__name__).info(
                "Logging configured | level=%s source=%s", level, config_file
            )
            return
        except Exception as exc:
            # Non-fatal — fall through to console handler
            logging.warning("Could not load %s: %s — falling back to stderr", config_file, exc)

    config = build_logging_config(log_level=level)
    logging.config.dictConfig(config)
    logging.getLogger(__name__).info(
        "Logging configured | level=%s destination=stderr (console)", level
    )
