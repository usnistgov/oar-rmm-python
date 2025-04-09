from fastapi import APIRouter, Path, Query, HTTPException
from typing import Optional
from app.crud.metrics import metrics_crud

router = APIRouter(
    prefix="/usagemetrics",
    tags=["metrics"],
)

@router.get("/records/{record_id:path}")
async def get_record_metrics(record_id: str = Path(..., description="Record ID to get metrics for")):
    """Get metrics for a specific record/dataset"""
    # Handle ARK identifiers
    if "ark:" in record_id:
        # Process ARK ID format
        parts = record_id.split("/")
        if len(parts) >= 3:
            record_id = f"{parts[0]}/{parts[1]}/{parts[2]}"
    
    metrics = metrics_crud.get_record_metrics(record_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics for record {record_id} not found")
    return metrics

@router.get("/records")
async def get_records_metrics(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    sort_by: str = Query("downloads", description="Sort by field (downloads or users)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)")
):
    """
    Get metrics for multiple records/datasets with pagination and sorting
    
    Returns:
        dict: Paginated list of record metrics
    """
    # Convert sort parameters
    sort_direction = -1 if sort_order.lower() == "desc" else 1
    sort_field = "users" if sort_by.lower() == "users" else "downloads"
    
    return metrics_crud.get_record_metrics_list(
        page=page, 
        size=size, 
        sort_by=sort_field,
        sort_order=sort_direction
    )

@router.get("/files/{file_path:path}")
async def get_file_metrics(file_path: str = Path(..., description="File path to get metrics for")):
    """Get metrics for a specific file"""
    # Handle paths with record IDs embedded
    record_id = ""
    file_id = file_path
    
    record_id = ""
    file_id = file_path
    print("*****",file_path)
    if "ark:" in file_path:
        # Process ARK ID format
        parts = file_path.split("/")
        if len(parts) >= 3:
            record_id = f"{parts[0]}/{parts[1]}/{parts[2]}"
            file_id = ""
    # Process paths like /recordid/filename.ext
     elif "/" in file_path:
        parts = file_path.split("/")
        if len(parts) >= 2:
            record_id = parts[0]
            file_id = "/".join(parts[1:])
    
    print("TESTING HERE 1",file_id)
    print("TESTING HERE 2",record_id)
    
    metrics = metrics_crud.get_file_metrics(file_path, record_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics for file {file_path} not found")
    return metrics

@router.get("/files")
async def get_files_metrics(
    sort_by: str = Query("downloads", description="Sort by field (downloads or filepath)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)")
):
    """
    Get metrics for all files with sorting
    
    Returns:
        dict: Complete list of file metrics
    """
    # Convert sort parameters
    sort_direction = -1 if sort_order.lower() == "desc" else 1
    sort_field = "filepath" if sort_by.lower() == "filepath" else "downloads"
    
    return metrics_crud.get_file_metrics_list(
        sort_by=sort_field,
        sort_order=sort_direction
    )

@router.get("/repo")
async def get_repo_metrics():
    """
    Get repository-level metrics
    
    Returns:
        dict: Repository metrics
    """
    return metrics_crud.get_repo_metrics()

@router.get("/totalusers")
async def get_unique_users():
    """
    Get total unique users count
    
    Returns:
        dict: Total unique users count
    """
    return metrics_crud.get_total_unique_users()
