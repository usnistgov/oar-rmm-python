from fastapi import APIRouter, Query, Body, Request
from typing import List, Optional, Dict, Any
from app.crud.patent import patent_crud

router = APIRouter()

@router.get("/patents/")
@router.get("/patents")
async def search_patents(
    reqest: Request,
    searchphrase: Optional[str] = Query(None, description="Text to search for"),
    skip: int = Query(0, description="Number of patents to skip"),
    limit: int = Query(10, description="Maximum number of patents to return"),
    sort_asc: Optional[List[str]] = Query(None, description="Fields to sort ascending"),
    sort_desc: Optional[List[str]] = Query(None, description="Fields to sort descending"),
    include: Optional[List[str]] = Query(None, description="Fields to include"),
    exclude: Optional[List[str]] = Query(None, description="Fields to exclude"),
    laboratory: Optional[str] = Query(None, description="Filter by laboratory"),
    status: Optional[str] = Query(None, description="Filter by status"),
    file_date: Optional[str] = Query(None, description="Filter by file date (YYYY-MM-DD)")
):
    """Search patents with various filters"""
    search_params = {
        "searchphrase": searchphrase,
        "skip": skip,
        "limit": limit,
        "sort_asc": sort_asc,
        "sort_desc": sort_desc,
        "include": include,
        "exclude": exclude
    }
    
    # Add optional filters
    if laboratory:
        search_params["Laboratory 1"] = laboratory
    if status:
        search_params["Status"] = status
    if file_date:
        search_params["File Date"] = file_date
        
    return patent_crud.search(**search_params)

@router.get("/patents/{patent_id}")
async def get_patent(patent_id: str):
    """Get a patent by ID or patent number"""
    return patent_crud.get(patent_id)