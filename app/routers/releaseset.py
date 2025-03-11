from fastapi import APIRouter, Query, Body, Depends, Request
from typing import List, Optional, Dict, Any
from app.crud.releaseset import releaseset_crud
from app.middleware.dependencies import validate_search_params

router = APIRouter()

@router.get("/releasesets/")
@router.get("/releasesets")
async def search_releasesets(request: Request, params: Dict[str, Any] = Depends(validate_search_params)):
    """
    Search release sets in the database.
    
    Args:
        params (Dict[str, Any]): Search parameters including:
            - searchphrase (str, optional): Text to search for
            - skip (int, optional): Number of records to skip
            - limit (int, optional): Maximum records to return
            - include (List[str], optional): Fields to include
            - exclude (List[str], optional): Fields to exclude
            - sort.desc/sort.asc (str, optional): Fields to sort by
            
    Returns:
        Dict: {
            "ResultData": List of matched release sets,
            "ResultCount": Total number of matches,
            "PageSize": Number of records per page,
            "Metrics": Query execution metrics
        }
    """
    return releaseset_crud.search(**params)

# @router.post("/releasesets/")
# async def create_releaseset(request: Request, data: Dict[str, Any] = Body(..., description="Release set data to create")):
#     """
#     Create a new release set entry.
    
#     Args:
#         data (Dict[str, Any]): The release set data to create
        
#     Returns:
#         Dict: The newly created release set with ID and metadata
#     """
#     return releaseset_crud.create(data)

@router.get("/releasesets/{releaseset_id}")
async def get_releaseset(request: Request, releaseset_id: str):
    """
    Get a single release set by ID.
    
    Args:
        releaseset_id (str): The ID of the release set to retrieve
        
    Returns:
        Dict: The release set data with metadata
    """
    return releaseset_crud.get(releaseset_id)