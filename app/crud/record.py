from typing import List, Dict, Any
from app.models.record import Record
from app.schemas.record import RecordCreate
from app.database import db
from bson.objectid import ObjectId

def get_record(record_id: str) -> Record:
    record = db.records.find_one({"_id": ObjectId(record_id)})
    if record:
        record['_id'] = str(record['_id'])
    return Record(**record) if record else None

def create_record(record: RecordCreate) -> Record:
    record_dict = record.dict()
    result = db.records.insert_one(record_dict)
    new_record = db.records.find_one({"_id": result.inserted_id})
    new_record['_id'] = str(new_record['_id'])
    return Record(**new_record)

def get_records(skip: int = 0, limit: int = 10) -> List[Record]:
    records = list(db.records.find().skip(skip).limit(limit))
    for record in records:
        record['_id'] = str(record['_id'])
    return [Record(**record) for record in records]

def search_records(query: str, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
    cursor = db.records.find({"$text": {"$search": query}}).skip(skip).limit(limit)
    records = list(cursor)
    for record in records:
        record['_id'] = str(record['_id'])
    result_data = [Record(**record) for record in records]
    result_count = db.records.count_documents({"$text": {"$search": query}})
    return {
        "ResultCount": result_count,
        "PageSize": limit,
        "ResultData": result_data
    }