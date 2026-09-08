"""Router for the ``/patents`` endpoints (the patents resource catalog).

Thin HTTP layer that validates query parameters via
``app.middleware.dependencies.validate_search_params``, remaps legacy/friendly
parameter names (``sort_asc``/``sort_desc``, ``laboratory``, ``status``,
``file_date``) to the field names actually used in the patents documents, and
delegates business logic to ``app.crud.patent.patent_crud``.
"""
from fastapi import APIRouter, Depends, Request
from typing import Dict, Any
from app.crud.patent import patent_crud
from app.middleware.dependencies import validate_search_params

router = APIRouter()

@router.get("/patents/")
@router.get("/patents")
async def search_patents(request: Request, params: Dict[str, Any] = Depends(validate_search_params)):
    """
    Search patents in the database.

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
    # Backward-compatible parameter mapping
    if "sort_asc" in params:
        params["sort.asc"] = params.pop("sort_asc")
    if "sort_desc" in params:
        params["sort.desc"] = params.pop("sort_desc")
    if "laboratory" in params:
        params["Laboratory 1"] = params.pop("laboratory")
    if "status" in params:
        params["Status"] = params.pop("status")
    if "file_date" in params:
        params["File Date"] = params.pop("file_date")

    return patent_crud.search(**params)

@router.get("/patents/{patent_id}")
async def get_patent(patent_id: str):
    """Get a patent by MongoDB ID or patent number.

    Args:
        patent_id: A MongoDB ``_id`` string or a value matching the
            ``"Patent #"`` field.

    Returns:
        Dict: The patent result envelope from ``patent_crud.get``.

    Raises:
        ValueError: If no patent matches either the ID or patent number.
    """
    return patent_crud.get(patent_id)