"""FastAPI dependency for validating search query parameters.

Used by most routers as ``params: Dict[str, Any] = Depends(validate_search_params)``
so that malformed query parameters (e.g. null bytes, path-traversal sequences,
misordered ``searchphrase``) are rejected before reaching the CRUD layer.
"""
from fastapi import Request
from typing import Dict, Any
from app.middleware.request_processor import ProcessRequest
from app.middleware.exceptions import IllegalArgumentException, InternalServerException

async def validate_search_params(request: Request) -> Dict[str, Any]:
    """Validate a request's raw query parameters before the route handler runs.

    Delegates the actual validation rules to
    :meth:`~app.middleware.request_processor.ProcessRequest.validate_input`.
    Intended to be used as a FastAPI dependency.

    Args:
        request: The incoming FastAPI request.

    Returns:
        Dict[str, Any]: The request's query parameters as a plain dict, once
        validated.

    Raises:
        IllegalArgumentException: If any parameter fails validation.
        InternalServerException: If validation itself fails unexpectedly.
    """
    processor = ProcessRequest()
    params = dict(request.query_params)
    
    try:
        processor.validate_input(params)
        return params
    except IllegalArgumentException as e:
        # Let the global exception handler manage this
        raise
    except Exception as e:
        # Wrap other errors in InternalServerException
        raise InternalServerException(str(request.url))