from fastapi import APIRouter, Query, Body, Depends, Request
from typing import List, Optional, Dict, Any
from app.crud.version import version_crud
from app.middleware.dependencies import validate_search_params

router = APIRouter()

@router.get("/versions/")
@router.get("/versions")
async def search_versions(request: Request, params: Dict[str, Any] = Depends(validate_search_params)):
    """
    Search version entries in the database.
    
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
            "ResultData": List of matched version entries,
            "ResultCount": Total number of matches,
            "PageSize": Number of records per page,
            "Metrics": Query execution metrics
        }
    """
    return version_crud.search(**params)

@router.get("/versions/{version_id}")
async def get_version(request: Request, version_id: str):
    """
    Get a single version entry by ID.
    
    Args:
        version_id (str): The ID of the version to retrieve
        
    Returns:
        Dict: The version data with metadata
    """
    return version_crud.get(version_id)