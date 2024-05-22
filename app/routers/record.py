from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.schemas.record import Record, RecordCreate
from app.crud import record as crud
from app.schemas.response import SearchResult

router = APIRouter()

@router.get("/records/", response_model=List[Record])
def read_records(skip: int = 0, limit: int = 10):
    records = crud.get_records(skip=skip, limit=limit)
    return records

@router.post("/records/", response_model=Record)
def create_record(record: RecordCreate):
    return crud.create_record(record)

@router.get("/records/{record_id}", response_model=Record)
def read_record(record_id: str):
    record = crud.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

@router.get("/records/search/", response_model=SearchResult)
def search_records(query: str = Query(..., min_length=1), skip: int = 0, limit: int = 10):
    search_results = crud.search_records(query, skip=skip, limit=limit)
    return search_results