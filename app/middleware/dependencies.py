from fastapi import Request, HTTPException
from typing import Dict, Any
from app.middleware.request_processor import ProcessRequest

async def validate_search_params(request: Request) -> Dict[str, Any]:
    """Validate and process search parameters before they reach the endpoint"""
    processor = ProcessRequest()
    params = dict(request.query_params)
    
    try:
        processor.validate_input(params)
        return params
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))