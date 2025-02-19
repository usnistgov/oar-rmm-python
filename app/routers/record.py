from fastapi import APIRouter, Query
from typing import List, Optional, Dict, Any
from app.crud.record import record_crud

router = APIRouter()

@router.get("/records/")
@router.get("/records")
async def search_records(
    searchphrase: Optional[str] = Query(None, description="Text to search for"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(10, description="Maximum number of records to return"),
    sort_asc: Optional[List[str]] = Query(None, description="Fields to sort ascending"),
    sort_desc: Optional[List[str]] = Query(None, description="Fields to sort descending"),
    include: Optional[List[str]] = Query(None, description="Fields to include"),
    exclude: Optional[List[str]] = Query(None, description="Fields to exclude"),
    logical_op: str = Query("AND", description="Logical operator for conditions"),
):
    return record_crud.search(
        searchphrase=searchphrase,
        skip=skip,
        limit=limit,
        sort_asc=sort_asc,
        sort_desc=sort_desc,
        include=include,
        exclude=exclude,
        logical_op=logical_op
    )
# @router.post("/records/")
# async def create_record(data: Dict[str, Any]):
#     return record_crud.create(data)

@router.get("/records/{record_id}")
async def get_record(record_id: str):
    return record_crud.get(record_id)