from typing import List, Dict, Any
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

def search_records(query: str, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
    start_time = time.time()

    cursor = db.records.find({"$text": {"$search": query}}).skip(skip).limit(limit)
    records = list(cursor)

    end_time = time.time()
    elapsed_time = end_time - start_time

    for record in records:
        record['_id'] = str(record['_id'])
    result_data = [Record(**record) for record in records]
    result_count = db.records.count_documents({"$text": {"$search": query}})
    return {
         "Metrics": {
            "ElapsedTime": elapsed_time
        },
        "ResultCount": result_count,
        "PageSize": limit,
        "ResultData": result_data,
       
    }