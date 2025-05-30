from fastapi import APIRouter, Query, Depends, Body, Request
from typing import List, Optional, Dict, Any
from app.crud.code import code_crud
from app.middleware.dependencies import validate_search_params

router = APIRouter()

@router.get("/code/")
@router.get("/code")
async def search_code(request: Request, params: Dict[str, Any] = Depends(validate_search_params)):
    """
    Search code entries in the database.
    
    Args:
        params (Dict[str, Any]): Search parameters including:
            - searchphrase (str, optional): Text to search for
            - skip (int, optional): Number of records to skip
            - limit (int, optional): Maximum records to return
            - sort.desc/sort.asc (str, optional): Fields to sort by
            
    Returns:
        Dict: {
            "ResultData": List of matched records,
            "ResultCount": Total number of matches,
            "PageSize": Number of records per page,
            "Metrics": Query execution metrics
        }
    """
    return code_crud.search(**params)

@router.get("/code/{code_id}")
async def get_code(request: Request, code_id: str):
    """
    Get a single code entry by ID
    """
    return code_crud.get(code_id)