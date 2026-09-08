"""Router for the ``/usagemetrics`` endpoints (record/file/repo/user download metrics).

Thin HTTP layer delegating to ``app.crud.metrics.metrics_crud``. Response
payloads are passed through :func:`sanitize_response` before being returned so
that non-JSON-compliant floats (``NaN``/``inf``) and raw ``datetime`` objects
never reach the client as invalid JSON.
"""
from fastapi import APIRouter, Path, Query, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional
from app.crud.metrics import metrics_crud
import math

router = APIRouter(
    prefix="/usagemetrics",
    tags=["metrics"],
)

def sanitize_response(data: dict) -> dict:
    """Recursively sanitize a response payload to guarantee valid JSON output.

    Replaces non-finite floats (``NaN``/``inf``/``-inf``) with ``0`` and
    converts any ``datetime``-like object (anything with an ``isoformat``
    method) to its ISO-8601 string form, recursing through nested dicts and
    lists.

    Args:
        data: The response payload to sanitize.

    Returns:
        dict: A JSON-safe copy of ``data`` (or ``data`` unchanged if falsy).
    """
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

def _collapse_query_params(query_params) -> dict:
    """Flatten multi-value query params by joining repeated keys."""
    collapsed = {}
    for key, value in query_params.multi_items():
        if key in collapsed:
            collapsed[key] = f"{collapsed[key]},{value}"
        else:
            collapsed[key] = value
    return collapsed

@router.get("/records/{record_id:path}")
async def get_record_metrics(record_id: str = Path(..., description="Record ID to get metrics for")):
    """Get download/usage metrics for a single record/dataset.

    Args:
        record_id: PDR ID, EDIID, or ``@id`` of the record.

    Returns:
        JSONResponse: Sanitized metrics payload for the record.

    Raises:
        HTTPException: 404 if no metrics exist for ``record_id``.
    """
    metrics = metrics_crud.get_record_metrics(record_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Metrics for record {record_id} not found")
    return JSONResponse(content=sanitize_response(metrics))

@router.get("/records")
async def get_records_metrics(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    sort_by: str = Query("total_size_download", description="Sort by field (total_size_download or users)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)")
):
    """Get a paginated, sorted list of metrics across all records/datasets.

    Args:
        page: 1-based page number.
        size: Number of results per page (1-100).
        sort_by: Field to sort by (``"total_size_download"`` or ``"users"``).
        sort_order: ``"asc"`` or ``"desc"``.

    Returns:
        JSONResponse: Sanitized paginated record-metrics payload.
    """
    metrics = metrics_crud.get_record_metrics_list(
        page=page, 
        size=size, 
        sort_by=sort_by,
        sort_order=-1 if sort_order.lower() == "desc" else 1
    )
    return JSONResponse(content=sanitize_response(metrics))

@router.get("/files/{file_path:path}")
async def get_file_metrics(file_path: str = Path(..., description="File path to get metrics for")):
    """Get download metrics for a specific file, identified by an ARK/record-scoped path.

    Parses ``file_path`` to separate a record identifier (ARK ID or plain
    record ID prefix) from the file-relative path, then delegates to
    :meth:`app.crud.metrics.MetricsCRUD.get_file_metrics`.

    Args:
        file_path: Combined ``{record_id}/{file_path}`` path segment, or an
            ``ark:.../...`` style path.

    Returns:
        JSONResponse: Sanitized metrics payload for the file.

    Raises:
        HTTPException: 404 if no metrics exist for the resolved file.
    """
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
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=0, le=500, description="Page size (0 returns all records)"),
    sort_by: Optional[str] = Query(
        None,
        description="Legacy sort field fallback (downloads or filepath)"
    ),
    sort_order: str = Query("desc", description="Legacy sort order (asc or desc)"),
    sort_desc: Optional[str] = Query(None, alias="sort.desc", description="Comma-separated fields to sort descending"),
    sort_asc: Optional[str] = Query(None, alias="sort.asc", description="Comma-separated fields to sort ascending")
):
    """Get a paginated, sorted, filterable list of metrics across all files.

    Args:
        request: The incoming request, used to collect arbitrary filter
            query parameters beyond the explicitly declared ones.
        page: 1-based page number.
        size: Number of results per page (0 returns all).
        sort_by: Legacy single-field sort fallback.
        sort_order: Legacy sort direction for ``sort_by``.
        sort_desc: Comma-separated fields to sort descending (preferred).
        sort_asc: Comma-separated fields to sort ascending (preferred).

    Returns:
        JSONResponse: Sanitized paginated file-metrics payload.
    """
    params = _collapse_query_params(request.query_params)
    params["page"] = str(page)
    params["size"] = str(size)

    if sort_desc:
        params["sort.desc"] = sort_desc
        params.pop("sort.asc", None)
    elif sort_asc:
        params["sort.asc"] = sort_asc
        params.pop("sort.desc", None)
    elif sort_by:
        key = "sort.desc" if sort_order.lower() == "desc" else "sort.asc"
        params[key] = sort_by

    metrics = metrics_crud.get_file_metrics_list(params)
    return JSONResponse(content=sanitize_response(metrics))

@router.get("/repo")
async def get_repo_metrics():
    """Get repository-level usage metrics (aggregated download/user totals).

    Returns:
        JSONResponse: Sanitized repository-metrics payload.
    """
    metrics = metrics_crud.get_repo_metrics()
    return JSONResponse(content=sanitize_response(metrics))

@router.get("/totalusers")
async def get_unique_users(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=0, le=500, description="Page size (0 returns all records)"),
    sort_desc: Optional[str] = Query(None, alias="sort.desc", description="Comma-separated fields to sort descending"),
    sort_asc: Optional[str] = Query(None, alias="sort.asc", description="Comma-separated fields to sort ascending")
):
    """Get a paginated count of unique users matching optional filters.

    Args:
        request: The incoming request, used to collect arbitrary filter
            query parameters beyond the explicitly declared ones.
        page: 1-based page number.
        size: Number of results per page (0 returns all).
        sort_desc: Comma-separated fields to sort descending.
        sort_asc: Comma-separated fields to sort ascending.

    Returns:
        JSONResponse: ``{"TotalUsersCount": int}``, sanitized for JSON output.
    """
    params = _collapse_query_params(request.query_params)
    params["page"] = str(page)
    params["size"] = str(size)

    # Only send one explicit sort directive downstream
    if sort_desc:
        params["sort.desc"] = sort_desc
        params.pop("sort.asc", None)
    elif sort_asc:
        params["sort.asc"] = sort_asc
        params.pop("sort.desc", None)

    metrics = metrics_crud.get_total_unique_users(params)
    return JSONResponse(content=sanitize_response({"TotalUsersCount": metrics.get("TotalUsersCount", 0)}))