"""Custom exception hierarchy and error-response shape for the RMM API.

All application-level errors that should produce a well-formed JSON error
response (rather than an opaque 500) derive from :class:`RMMException`. Each
subclass corresponds to one of the global handlers registered in
``app.main`` (e.g. :class:`ResourceNotFoundException` -> HTTP 404,
:class:`IllegalArgumentException` -> HTTP 400). :class:`ErrorInfo` defines the
common JSON body shape returned by those handlers.
"""
from fastapi import HTTPException, Request
from typing import Optional, Dict, Any

class ErrorInfo:
    """
    Error information structure to be used in the response
    """
    def __init__(self, url: str, message: str, http_status: str):
        """Store the fields of a standardized API error response.

        Args:
            url: The request URL that produced the error.
            message: Human-readable error message.
            http_status: The HTTP status code, as a string (e.g. ``"404"``).
        """
        self.url = url
        self.message = message
        self.http_status = http_status
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize this error to the JSON-compatible dict returned to clients.

        Returns:
            dict: ``{"url": str, "message": str, "httpStatus": str}``.
        """
        return {
            "url": self.url,
            "message": self.message,
            "httpStatus": self.http_status
        }


class RMMException(Exception):
    """Base exception for RMM application"""
    def __init__(self, request_url: Optional[str] = None, message: Optional[str] = None):
        """Store the request URL and message shared by all RMM exceptions.

        Args:
            request_url: URL of the request that triggered the error, if known.
            message: Human-readable error message; a generic default is used
                if omitted.
        """
        self.request_url = request_url
        self.message = message or "Resource you are looking for is not available."
        super().__init__(self.message)


class GeneralException(RMMException):
    """Catch-all exception for application errors that don't fit a more specific type."""
    def __init__(self, request_url: Optional[str] = None, message: Optional[str] = None):
        default_message = "Exception thrown for this request."
        super().__init__(request_url, message or default_message)


class IllegalArgumentException(RMMException):
    """Raised when request parameters are invalid, malformed, or missing (mapped to HTTP 400)."""
    def __init__(self, message: str = None, request_url: Optional[str] = None):
        msg = message or "Parameters are misplaced or values are missing."
        super().__init__(request_url, msg)


class ResourceNotFoundException(RMMException):
    """Raised when a requested resource (e.g. record, field) does not exist (mapped to HTTP 404)."""
    def __init__(self, message: str = None, request_url: Optional[str] = None):
        msg = message or "Resource you are looking for is not available."
        super().__init__(request_url, msg)


class KeyWordNotFoundException(RMMException):
    """Raised when a search yields no matching documents (mapped to HTTP 404)."""
    def __init__(self, message: str = None, request_url: Optional[str] = None):
        msg = message or "Keywords you are looking for are not available."
        super().__init__(request_url, msg)


class InternalServerException(RMMException):
    """Raised for unexpected server-side/database failures (mapped to HTTP 500)."""
    def __init__(self, message: str = None, request_url: Optional[str] = None):
        msg = message or "There is an error running your query on the server."
        super().__init__(request_url, msg)