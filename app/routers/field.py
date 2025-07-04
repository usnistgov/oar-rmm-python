from fastapi import APIRouter, Query, Body, Depends, Request
from typing import List, Optional, Dict, Any
from app.crud.field import field_crud
from app.middleware.dependencies import validate_search_params
from app.middleware.exceptions import KeyWordNotFoundException, InternalServerException, IllegalArgumentException

import logging

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/records",
    tags=["fields"]
)

@router.get("/fields/")
@router.get("/fields")
async def search_fields(request: Request):
    # Fetch all fields directly without pagination
    fields = field_crud.get_all(limit=0)
    # Return just the list, no extra metadata
    return fields

# async def search_fields(request: Request, params: Dict[str, Any] = Depends(validate_search_params)):
#     """
#     Search fields in the database.
    
#     Args:
#         params (Dict[str, Any]): Search parameters including:
#             - searchphrase (str, optional): Text to search for
#             - skip (int, optional): Number of records to skip
#             - limit (int, optional): Maximum records to return
#             - include (List[str], optional): Fields to include
#             - exclude (List[str], optional): Fields to exclude
#             - sort.desc/sort.asc (str, optional): Fields to sort by
            
#     Returns:
#         Dict: {
#             "ResultData": List of matched fields,
#             "ResultCount": Total number of matches,
#             "PageSize": Number of records per page,
#             "Metrics": Query execution metrics
#         }
        
#     Raises:
#         KeyWordNotFoundException: If no fields found matching the criteria
#         InternalServerException: If there is an error processing the request
#     """
#     try:
#         # If no search parameters provided, get all fields
#         if not params.get('searchphrase') and not any(key for key in params if key not in ['skip', 'limit', 'size', 'page']):
#             result = field_crud.get_all(
#                 skip=params.get('skip', 0),
#                 limit=params.get('limit', 10)
#             )
#         else:
#             # Perform search with specified parameters
#             result = field_crud.search(**params)
        
#         # Check if no results found
#         if not result.get('ResultData'):
#             logger.info(f"No fields found with parameters: {params}")
#             raise KeyWordNotFoundException(str(request.url))
        
#         return result
        
#     except KeyWordNotFoundException:
#         # Re-raise for consistent error handling
#         raise
#     except Exception as e:
#         logger.error(f"Error searching fields: {str(e)}")
#         raise InternalServerException(str(request.url))

@router.get("/fields/{field_id}")
async def get_field(request: Request, field_id: str):
    """
    Get a single field by ID.
    
    Args:
        field_id (str): The ID of the field to retrieve
        
    Returns:
        Dict: The field data with metadata
        
    Raises:
        KeyWordNotFoundException: If the field with the specified ID is not found
        InternalServerException: If there is an error processing the request
    """
    try:
        result = field_crud.get(field_id)
        if not result.get('ResultData'):
            raise KeyWordNotFoundException(f"Field with ID {field_id} not found")
        return result
        
    except KeyWordNotFoundException:
        # Re-raise for consistent error handling
        raise
    except Exception as e:
        logger.error(f"Error retrieving field {field_id}: {str(e)}")
        raise InternalServerException(str(request.url))
