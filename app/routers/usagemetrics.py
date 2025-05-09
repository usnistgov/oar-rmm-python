from fastapi import APIRouter, Path, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from app.crud.metrics import metrics_crud
import math

router = APIRouter(
    prefix="/usagemetrics",
    tags=["metrics"],
)

def sanitize_response(data: dict) -> dict:
    """Sanitize the response data to ensure JSON compliance"""
    if not data:
        return data
        
    def sanitize_value(v):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return 0
        elif isinstance(v, dict):
            return {k: sanitize_value(val) for k, val in v.items()}
        elif isinstance(v, list):
            return [sanitize_value(item) for item in v]
        # datetime handling
        elif hasattr(v, 'isoformat'):  # This catches datetime objects
            return v.isoformat()
        return v
        
    return sanitize_value(data)

@router.get("/records/{record_id:path}")
async def get_record_metrics(record_id: str = Path(..., description="Record ID to get metrics for")):
    """Get metrics for a specific record/dataset"""
    metrics = metrics_crud.get_record_metrics(record_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics for record {record_id} not found")
    return JSONResponse(content=sanitize_response(metrics))

@router.get("/records")
async def get_records_metrics(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    sort_by: str = Query("downloads", description="Sort by field (downloads or users)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)")
):
    """Get metrics for multiple records/datasets with pagination and sorting"""
    metrics = metrics_crud.get_record_metrics_list(
        page=page, 
        size=size, 
        sort_by=sort_by,
        sort_order=-1 if sort_order.lower() == "desc" else 1
    )
    return JSONResponse(content=sanitize_response(metrics))

@router.get("/files/{file_path:path}")
async def get_file_metrics(file_path: str = Path(..., description="File path to get metrics for")):
    """Get metrics for a specific file"""
    record_id = ""
    file_id = file_path
    
    if "ark:" in file_path:
        parts = file_path.split("/")
        if len(parts) >= 3:
            record_id = f"{parts[0]}/{parts[1]}/{parts[2]}"
            file_id = ""
    elif "/" in file_path:
        parts = file_path.split("/")
        if len(parts) >= 2:
            record_id = parts[0]
            file_id = "/".join(parts[1:])
    
    metrics = metrics_crud.get_file_metrics(file_id, record_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics for file {file_path} not found")
    return JSONResponse(content=sanitize_response(metrics))

@router.get("/files")
async def get_files_metrics(
    sort_by: str = Query("downloads", description="Sort by field (downloads or filepath)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)")
):
    """Get metrics for all files with sorting"""
    metrics = metrics_crud.get_file_metrics_list(
        sort_by=sort_by,
        sort_order=-1 if sort_order.lower() == "desc" else 1
    )
    return JSONResponse(content=sanitize_response(metrics))

@router.get("/repo")
async def get_repo_metrics():
    """Get repository-level metrics"""
    metrics = metrics_crud.get_repo_metrics()
    return JSONResponse(content=sanitize_response(metrics))

@router.get("/totalusers")
async def get_unique_users():
    """Get total unique users count"""
    metrics = metrics_crud.get_total_unique_users()
    return JSONResponse(content=sanitize_response(metrics))