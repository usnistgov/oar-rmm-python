from fastapi import APIRouter, Query, Body, Request
from typing import List, Optional, Dict, Any
from app.crud.field import field_crud

router = APIRouter()

@router.get("/fields/")
@router.get("/fields")
async def search_fields(
    reqest: Request,
    searchphrase: Optional[str] = Query(None, description="Text to search for"),
    skip: int = Query(0, description="Number of fields to skip"),
    limit: int = Query(10, description="Maximum number of fields to return"),
    sort_asc: Optional[List[str]] = Query(None, description="Fields to sort ascending"),
    sort_desc: Optional[List[str]] = Query(None, description="Fields to sort descending"),
    include: Optional[List[str]] = Query(None, description="Fields to include"),
    exclude: Optional[List[str]] = Query(None, description="Fields to exclude"),
    logical_op: str = Query("AND", description="Logical operator for conditions"),
):
    return field_crud.search(
        searchphrase=searchphrase,
        skip=skip,
        limit=limit,
        sort_asc=sort_asc,
        sort_desc=sort_desc,
        include=include,
        exclude=exclude,
        logical_op=logical_op
    )

@router.post("/fields/")
async def create_field(
    reqest: Request, data: Dict[str, Any] = Body(..., description="Field data to create")
):
    return field_crud.create(data)

@router.get("/fields/{field_id}")
async def get_field(
    reqest: Request, field_id: str
):
    return field_crud.get(field_id)