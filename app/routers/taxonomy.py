from fastapi import APIRouter, Query, Body, Depends, Request
from typing import List, Optional, Dict, Any
from app.crud.taxonomy import taxonomy_crud
from app.middleware.dependencies import validate_search_params

router = APIRouter()

@router.get("/taxonomy/")
@router.get("/taxonomy")
async def search_taxonomy(request: Request, params: Dict[str, Any] = Depends(validate_search_params)):
    """
    Search taxonomy entries in the database.
    
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
            "ResultData": List of matched taxonomy entries,
            "ResultCount": Total number of matches,
            "PageSize": Number of records per page,
            "Metrics": Query execution metrics
        }
    """
    return taxonomy_crud.search(**params)

# @router.post("/taxonomy/")
# async def create_taxonomy(request: Request, data: Dict[str, Any] = Body(..., description="Taxonomy data to create")):
#     """
#     Create a new taxonomy entry.
    
#     Args:
#         data (Dict[str, Any]): The taxonomy data to create
        
#     Returns:
#         Dict: The newly created taxonomy entry with ID and metadata
#     """
#     return taxonomy_crud.create(data)

@router.get("/taxonomy/{taxonomy_id}")
async def get_taxonomy(request: Request, taxonomy_id: str):
    """
    Get a single taxonomy entry by ID.
    
    Args:
        taxonomy_id (str): The ID of the taxonomy entry to retrieve
        
    Returns:
        Dict: The taxonomy data with metadata
    """
    return taxonomy_crud.get(taxonomy_id)