from fastapi import APIRouter, Query, Body, Depends, Request
from typing import List, Optional, Dict, Any
from app.crud.api import api_crud
from app.middleware.dependencies import validate_search_params

router = APIRouter()

@router.get("/apis/")
@router.get("/apis")
async def search_apis(request: Request, params: Dict[str, Any] = Depends(validate_search_params)):
    """
    Search APIs in the database.
    
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
            "ResultData": List of matched APIs,
            "ResultCount": Total number of matches,
            "PageSize": Number of records per page,
            "Metrics": Query execution metrics
        }
    """
    return api_crud.search(**params)

# @router.post("/apis/")
# async def create_api(data: Dict[str, Any]):
#     """
#     Create a new API entry.
    
#     Args:
#         data (Dict[str, Any]): The API data to create
        
#     Returns:
#         Dict: The newly created API with ID and metadata
#     """
#     return api_crud.create(data)

@router.get("/apis/{api_id}")
async def get_api(request: Request, api_id: str):
    """
    Get a single API by ID.
    
    Args:
        api_id (str): The ID of the API to retrieve
        
    Returns:
        Dict: The API data with metadata
    """
    return api_crud.get(api_id)