from fastapi import APIRouter, HTTPException, Request, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, root_validator
from fastapi.responses import JSONResponse
from app.schemas.response import SearchResult
from app.crud import record as crud

router = APIRouter()

class SearchParams(BaseModel):
    include: Optional[List[str]] = Field(default_factory=[])
    exclude: Optional[List[str]] = Field(default_factory=[])
    logicalOp: Optional[List[str]] = Field(default_factory=[])
    query: Optional[str] = None
    page: int = 0
    size: int = 10
    sort_desc: Optional[List[str]] = Field(default_factory=[])
    sort_asc: Optional[List[str]] = Field(default_factory=[])
    
    @root_validator(pre=True)
    def set_default_lists(cls, values):
        values['include'] = values.get('include', [])
        values['exclude'] = values.get('exclude', [])
        values['logicalOp'] = values.get('logicalOp', [])
        values['sort_desc'] = values.get('sort_desc', [])
        values['sort_asc'] = values.get('sort_asc', [])
        return values

def validate_query_string(params: SearchParams):
    print(params.dict())
    if params.logicalOp:
        for i, logical_op in enumerate(params.logicalOp):
            if logical_op and (i == 0 or (params.include and params.include[i - 1]) or (params.exclude and params.exclude[i - 1])):
                raise HTTPException(status_code=400, detail="There should be a key=value parameter after logicalOp.")

@router.get("/records/search/", response_model=SearchResult)
def search_records(
    request: Request,
    include: Optional[List[str]] = Query(default=[]),
    exclude: Optional[List[str]] = Query(default=[]),
    logicalOp: Optional[List[str]] = Query(default=[]),
    query: Optional[str] = Query(None),
    page: int = Query(0),
    size: int = Query(10),
    sort_desc: Optional[List[str]] = Query(default=[]),
    sort_asc: Optional[List[str]] = Query(default=[]),
):
    # Create the SearchParams object
    params = SearchParams(
        include=include,
        exclude=exclude,
        logicalOp=logicalOp,
        query=query,
        page=page,
        size=size,
        sort_desc=sort_desc,
        sort_asc=sort_asc
    )

    # Validate the query parameters
    validate_query_string(params)
    
    # Perform the search
    search_results = crud.search_records(
        query=params.query or "",
        skip=params.page * params.size,
        limit=params.size,
        sort_desc=params.sort_desc,
        sort_asc=params.sort_asc
    )
    
    return JSONResponse(content={
        "Metrics": search_results["Metrics"],
        "ResultCount": search_results["ResultCount"],
        "PageSize": search_results["PageSize"],
        "ResultData": search_results["ResultData"]
    })