"""Router for the ``/papers`` endpoints (the research-papers resource catalog).

Thin HTTP layer that validates query parameters via
``app.middleware.dependencies.validate_search_params``, remaps legacy
``sort_asc``/``sort_desc`` parameter names to ``sort.asc``/``sort.desc``, and
delegates business logic to ``app.crud.paper.paper_crud``.
"""
from fastapi import APIRouter, Depends, Request
from typing import Dict, Any
from app.crud.paper import paper_crud
from app.middleware.dependencies import validate_search_params

router = APIRouter()

@router.get("/papers/")
@router.get("/papers")
async def search_papers(request: Request, params: Dict[str, Any] = Depends(validate_search_params)):
    """
    Search papers in the database.
    
    Args:
        params (Dict[str, Any]): Search parameters including:
            - searchphrase (str, optional): Text to search for in papers
            - skip (int, optional): Number of results to skip
            - limit (int, optional): Maximum number of results to return
            - sort.desc/sort.asc (str, optional): Fields to sort by
        
    Returns:
        Dict: {
            "ResultData": List of matched records,
            "ResultCount": Total number of matches,
            "PageSize": Number of results per page,
            "Metrics": Query execution metrics
        }
    """
    # Backward-compatible parameter mapping
    if "sort_asc" in params:
        params["sort.asc"] = params.pop("sort_asc")
    if "sort_desc" in params:
        params["sort.desc"] = params.pop("sort_desc")

    return paper_crud.search(**params)


@router.get("/papers/{paper_id}")
async def get_paper(paper_id: str):
    """Get a paper by MongoDB ID or an alternate paper identifier.

    Args:
        paper_id: A MongoDB ``_id``, DOI, ``pubID``, or other identifier
            (see ``PaperCRUD.get`` for the full fallback lookup order).

    Returns:
        Dict: The paper result envelope from ``paper_crud.get``.

    Raises:
        ValueError: If no paper matches any of the attempted identifiers.
    """
    return paper_crud.get(paper_id)
