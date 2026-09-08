"""Cross-cutting request/response concerns for the RMM API.

Includes shared exception types (``app.middleware.exceptions``), the generic
query-parameter-to-MongoDB-query translator (``app.middleware.request_processor``),
a FastAPI dependency wrapping input validation (``app.middleware.dependencies``),
and an optional Starlette middleware for recording download metrics
(``app.middleware.metrics_middleware``).
"""
