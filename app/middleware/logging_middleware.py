"""HTTP request/response logging middleware.

Emits a ``→`` line when a request arrives and a ``←`` line when the response
is sent, with the HTTP method, path, status code, and elapsed milliseconds::

    2026-05-15 10:23:45.100 | INFO     | rmm.http                      | [a1b2c3d4] | → GET /rmm/records?searchphrase=laser
    2026-05-15 10:23:45.145 | INFO     | rmm.http                      | [a1b2c3d4] | ← 200  GET /rmm/records  45ms
    2026-05-15 10:23:46.200 | WARNING  | rmm.http                      | [b2c3d4e5] | ← 200  GET /rmm/records  623ms  ⚠ SLOW
    2026-05-15 10:23:47.010 | WARNING  | rmm.http                      | [c3d4e5f6] | ← 404  GET /rmm/records/no-such-id  12ms
    2026-05-15 10:23:48.020 | ERROR    | rmm.http                      | [d4e5f6a7] | ← 500  GET /rmm/records  8ms

Slow-request threshold defaults to 500 ms; override with the
``SLOW_REQUEST_THRESHOLD_MS`` environment variable.

Request IDs
-----------
A UUID is generated per request and stored in a ContextVar (via
``app.logging_setup.set_request_id``).  This means every log line emitted
anywhere in the codebase while handling that request — including CRUD modules,
database helpers, and exception handlers — is automatically tagged with the
same short ID.  No instrumentation is needed in routers or service code.

The full UUID is also returned to the caller in the ``X-Request-ID`` response
header, which makes it easy to correlate a specific API response with its log
entries by grepping the short ID.
"""

import os
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.logging_setup import set_request_id

logger = logging.getLogger("rmm.http")

_SLOW_MS: float = float(os.environ.get("SLOW_REQUEST_THRESHOLD_MS", "500"))

# Paths that generate no diagnostic value when logged every poll cycle
_SKIP_EXACT: frozenset = frozenset({"/", "/rmm/", "/favicon.ico"})
_SKIP_PREFIX: tuple = ("/static", "/rmm/static")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status, and elapsed time.

    Also assigns a short UUID to each request and stores it in a ContextVar
    so all log lines emitted during the request lifecycle are tagged with the
    same ID.  The full UUID is returned to the caller as ``X-Request-ID``.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate a hex UUID (32 chars); first 8 chars shown in log lines.
        request_id = uuid.uuid4().hex
        set_request_id(request_id)

        method = request.method
        path   = request.url.path
        is_noisy = path in _SKIP_EXACT or path.startswith(_SKIP_PREFIX)

        if not is_noisy:
            qs = request.url.query
            # Truncate very long query strings to keep log lines readable
            suffix = f"?{qs[:200]}" if qs else ""
            logger.info("\u2192 %s %s%s", method, path, suffix)

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "\u2715 %s %s  %.0fms  unhandled exception",
                method, path, elapsed_ms,
                exc_info=True,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000

        if not is_noisy:
            status = response.status_code
            if elapsed_ms >= _SLOW_MS:
                logger.warning(
                    "\u2190 %d  %s %s  %.0fms  \u26a0 SLOW",
                    status, method, path, elapsed_ms,
                )
            elif status >= 500:
                logger.error(
                    "\u2190 %d  %s %s  %.0fms",
                    status, method, path, elapsed_ms,
                )
            elif status >= 400:
                logger.warning(
                    "\u2190 %d  %s %s  %.0fms",
                    status, method, path, elapsed_ms,
                )
            else:
                logger.info(
                    "\u2190 %d  %s %s  %.0fms",
                    status, method, path, elapsed_ms,
                )

        # Expose the full ID to callers for client-side log correlation
        response.headers["X-Request-ID"] = request_id
        return response
