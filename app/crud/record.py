from typing import List, Dict, Any, Optional
from app.models.record import Record
from app.schemas.record import RecordCreate
from app.database import db
from bson.objectid import ObjectId
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SKIP = 0
DEFAULT_LIMIT = 10

def create_record(record: RecordCreate) -> Record:
    """
    Create a new record in the database.

    Args:
        record (RecordCreate): A Pydantic model representing the record to be created.

    Returns:
        Record: The newly created record, including its MongoDB ObjectId.

    Raises:
        ValueError: If the record cannot be created.

    Example:
        new_record = create_record(record)
    """
    try:
        record_dict = record.model_dump()  # Convert Pydantic model to dictionary
        result = db.records.insert_one(record_dict)  # Insert the record into the database
        new_record = db.records.find_one({"_id": result.inserted_id})  # Retrieve the newly created record
        new_record['_id'] = str(new_record['_id'])  # Convert ObjectId to string
        return Record(**new_record)  # Return the record as a Pydantic model
    except Exception as e:
        logger.error(f"Failed to create record: {e}")
        raise ValueError("Failed to create record")

def get_record(record_id: str) -> Dict[str, Any]:
    """
    Retrieve a single record from the database by its ID.

    Args:
        record_id (str): The ID of the record to retrieve.

    Returns:
        Dict[str, Any]: A dictionary containing the record data, including metrics.

    Raises:
        ValueError: If the record cannot be found.

    Example:
        record = get_record("record_id")
    """
    start_time = time.time()  # Start timing the operation

    try:
        record = db.records.find_one({"_id": ObjectId(record_id)})  # Find the record by its ObjectId
        if record:
            record['_id'] = str(record['_id'])  # Convert ObjectId to string
        else:
            raise ValueError("Record not found")
    except Exception as e:
        logger.error(f"Failed to retrieve record: {e}")
        raise ValueError("Failed to retrieve record")

    end_time = time.time()  # End timing the operation
    elapsed_time = end_time - start_time  # Calculate elapsed time

    result_data = [Record(**record)] if record else []  # Convert to Pydantic model if record exists
    result_count = 1 if record else 0  # Set result count
    return {
        "ResultCount": result_count,
        "PageSize": 1,
        "ResultData": result_data,
        "Metrics": {
            "ElapsedTime": elapsed_time
        }
    }

def get_records(skip: int = DEFAULT_SKIP, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
    """
    Retrieve multiple records from the database with pagination.

    Args:
        skip (int): The number of records to skip (default is 0).
        limit (int): The maximum number of records to return (default is 10).

    Returns:
        Dict[str, Any]: A dictionary containing the records data, including metrics.

    Raises:
        ValueError: If records cannot be retrieved.

    Example:
        records = get_records(skip=0, limit=10)
    """
    start_time = time.time()  # Start timing the operation

    try:
        records = list(db.records.find().skip(skip).limit(limit))  # Retrieve records with pagination
        for record in records:
            record['_id'] = str(record['_id'])  # Convert ObjectId to string
    except Exception as e:
        logger.error(f"Failed to retrieve records: {e}")
        raise ValueError("Failed to retrieve records")

    end_time = time.time()  # End timing the operation
    elapsed_time = end_time - start_time  # Calculate elapsed time

    result_data = [Record(**record) for record in records]  # Convert to Pydantic models
    result_count = db.records.count_documents({})  # Count total number of records
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
    skip: int = DEFAULT_SKIP, 
    limit: int = DEFAULT_LIMIT, 
    sort_desc: Optional[List[str]] = None, 
    sort_asc: Optional[List[str]] = None,
    include: Optional[List[str]] = None,  # new parameter
    exclude: Optional[List[str]] = None,  # new parameter
    logicalOp: Optional[str] = "AND"  # new parameter
) -> Dict[str, Any]:
    """
    Search for records in the database based on a query and additional parameters.

    Args:
        query (str): The search query string.
        skip (int): The number of records to skip (default is 0).
        limit (int): The maximum number of records to return (default is 10).
        sort_desc (Optional[List[str]]): Fields to sort in descending order.
        sort_asc (Optional[List[str]]): Fields to sort in ascending order.
        include (Optional[List[str]]): Fields to include in the search.
        exclude (Optional[List[str]]): Fields to exclude from the search.
        logicalOp (Optional[str]): Logical operation to apply (default is "AND").

    Returns:
        Dict[str, Any]: A dictionary containing the search results, including metrics.

    Raises:
        ValueError: If the search query fails.

    Example:
        results = search_records(query="example", skip=0, limit=10, sort_desc=["date"], include=["field1"], exclude=["field2"], logicalOp="OR")
    """
    logger.info(f'Searching records for query: {query}')
    start_time = time.time()  # Start timing the operation

    try:
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

        cursor = db.records.find(mongo_query).skip(skip).limit(limit)  # Execute the query with pagination
        if sort_params:
            cursor = cursor.sort(sort_params)  # Apply sorting if specified
            
        records = list(cursor)  # Convert cursor to list

        for record in records:
            if isinstance(record['_id'], ObjectId):
                record['_id'] = str(record['_id'])  # Convert ObjectId to string
        result_data = [Record(**record) for record in records]  # Convert to Pydantic models
        result_count = db.records.count_documents(mongo_query)  # Count total number of matching records
    except Exception as e:
        logger.error(f"Failed to search records: {e}")
        raise ValueError("Failed to search records")

    end_time = time.time()  # End timing the operation
    elapsed_time = end_time - start_time  # Calculate elapsed time

    logger.info(f'Search completed in {elapsed_time} seconds.')
    
    return {
        "Metrics": {
            "ElapsedTime": elapsed_time
        },
        "ResultCount": result_count,
        "PageSize": limit,
        "ResultData": [record.model_dump() for record in result_data],  # Convert Pydantic models to dictionaries
    }