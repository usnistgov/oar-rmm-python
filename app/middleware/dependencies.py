from fastapi import Request
from typing import Dict, Any
from app.middleware.request_processor import ProcessRequest
from app.middleware.exceptions import IllegalArgumentException, InternalServerException

async def validate_search_params(request: Request) -> Dict[str, Any]:
    """Validate and process search parameters before they reach the endpoint"""
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