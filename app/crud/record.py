from typing import List, Dict, Any, Optional
from app.models.record import Record
from app.schemas.record import RecordCreate
from app.database import db
from bson.objectid import ObjectId
import time


def create_record(record: RecordCreate) -> Record:
    record_dict = record.dict()
    result = db.records.insert_one(record_dict)
    new_record = db.records.find_one({"_id": result.inserted_id})
    new_record['_id'] = str(new_record['_id'])
    return Record(**new_record)

def get_record(record_id: str) -> Dict[str, Any]:
    start_time = time.time()

    record = db.records.find_one({"_id": ObjectId(record_id)})
    if record:
        record['_id'] = str(record['_id'])

    end_time = time.time()
    elapsed_time = end_time - start_time

    result_data = [Record(**record)] if record else []
    result_count = 1 if record else 0
    return {
        "ResultCount": result_count,
        "PageSize": 1,
        "ResultData": result_data,
        "Metrics": {
            "ElapsedTime": elapsed_time
        }
    }

def get_records(skip: int = 0, limit: int = 10) -> Dict[str, Any]:
    start_time = time.time()

    records = list(db.records.find().skip(skip).limit(limit))
    for record in records:
        record['_id'] = str(record['_id'])

    end_time = time.time()
    elapsed_time = end_time - start_time

    result_data = [Record(**record) for record in records]
    result_count = db.records.count_documents({})
    return {
        "ResultCount": result_count,
        "PageSize": limit,
        "ResultData": result_data,
        "Metrics": {
            "ElapsedTime": elapsed_time
        }
    }

def search_records(
    query: str, 
    skip: int = 0, 
    limit: int = 10, 
    sort_desc: Optional[List[str]] = None, 
    sort_asc: Optional[List[str]] = None,
    include: Optional[List[str]] = None,  # new parameter
    exclude: Optional[List[str]] = None,  # new parameter
    logicalOp: Optional[str] = "AND"  # new parameter
) -> Dict[str, Any]:
    print('Searching records for query: ', query, flush=True)
    start_time = time.time()

    # Build the sort parameters
    sort_params = []
    if sort_desc:
        for field in sort_desc:
            sort_params.append((field, -1))
    if sort_asc:
        for field in sort_asc:
            sort_params.append((field, 1))

    # Build the MongoDB query
    mongo_query = {"$text": {"$search": query}}

    # Apply the include and exclude parameters
    if include or exclude:
        field_query = {}
        if include:
            field_query["$all"] = include
        if exclude:
            field_query["$nin"] = exclude
        if logicalOp == "AND":
            mongo_query["$and"] = [mongo_query, field_query]
        elif logicalOp == "OR":
            mongo_query["$or"] = [mongo_query, field_query]

    cursor = db.records.find(mongo_query).skip(skip).limit(limit)
    if sort_params:
        cursor = cursor.sort(sort_params)
        
    records = list(cursor)

    end_time = time.time()
    elapsed_time = end_time - start_time

    for record in records:
        if isinstance(record['_id'], ObjectId):
            record['_id'] = str(record['_id'])
    result_data = [Record(**record) for record in records]
    result_count = db.records.count_documents(mongo_query)
    
    print('Search completed in ', elapsed_time, ' seconds.', flush=True)
    
    return {
        "Metrics": {
            "ElapsedTime": elapsed_time
        },
        "ResultCount": result_count,
        "PageSize": limit,
        "ResultData": [record.model_dump() for record in result_data],
    }