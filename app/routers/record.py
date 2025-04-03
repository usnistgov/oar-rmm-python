from fastapi import APIRouter, Query, Depends, Request
from typing import List, Optional, Dict, Any
from app.crud.record import record_crud
from app.middleware.dependencies import validate_search_params

router = APIRouter()

@router.get("/records/")
@router.get("/records")
async def search_records(reqest: Request, params: Dict[str, Any] = Depends(validate_search_params)):
    """
    Search record entries in the database.
    
    Args:
        params (Dict[str, Any]): Search parameters including:
            - searchphrase (str, optional): Text to search for
            - skip (int, optional): Number of records to skip
            - limit (int, optional): Maximum records to return
            - include/exclude (List[str], optional): Fields to include/exclude
            
    Returns:
        Dict: {
            "ResultData": List of matched records,
            "ResultCount": Total number of matches,
            "PageSize": Number of records per page,
            "Metrics": Query execution metrics
        }
    """
    return record_crud.search(**params)


# @router.post("/records/")
# async def create_record(data: Dict[str, Any]):
#     return record_crud.create(data)

@router.get("/records/{record_id}")
async def get_record(request: Request, record_id: str):
    """
    Get a record by ID or EDIID.
    
    Args:
        record_id: Either a MongoDB ID or an EDIID
        
    Returns:
        dict: The record data without wrapper
    """
    return record_crud.get(record_id)