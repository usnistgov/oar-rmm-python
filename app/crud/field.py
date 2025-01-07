from typing import List, Dict, Any, Optional
from app.models.field import FieldModel
from bson.objectid import ObjectId
from app.database import db
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_SKIP = 0
DEFAULT_LIMIT = 10

def get_field(field_id: str) -> Dict[str, Any]:
    """
    Retrieve a single field from the database by its ID.

    Args:
        field_id (str): The ID of the field to retrieve.

    Returns:
        Dict[str, Any]: A dictionary containing the field data, including metrics.

    Raises:
        ValueError: If the field cannot be found.

    Example:
        field = get_field("field_id")
    """
    start_time = time.time()

    try:
        field = db.fields.find_one({"_id": ObjectId(field_id)})
        if field:
            field['_id'] = str(field['_id'])
        else:
            raise ValueError("Field not found")
    except Exception as e:
        logger.error(f"Failed to retrieve field: {e}")
        raise ValueError("Failed to retrieve field")

    end_time = time.time()
    elapsed_time = end_time - start_time

    result_data = [FieldModel(**field)] if field else []
    result_count = 1 if field else 0
    return {
        "ResultCount": result_count,
        "PageSize": 1,
        "ResultData": result_data,
        "Metrics": {
            "ElapsedTime": elapsed_time
        }
    }

def get_fields(
    tags: Optional[List[str]] = None,
    skip: int = DEFAULT_SKIP,
    limit: int = DEFAULT_LIMIT
) -> Dict[str, Any]:
    """
    Retrieve multiple fields from the database with optional tag filtering and pagination.

    Args:
        tags (Optional[List[str]]): List of tags to filter fields by.
        skip (int): The number of fields to skip (default is 0).
        limit (int): The maximum number of fields to return (default is 10).

    Returns:
        Dict[str, Any]: A dictionary containing the fields data, including metrics.

    Raises:
        ValueError: If fields cannot be retrieved.

    Example:
        fields = get_fields(tags=["searchable"], skip=0, limit=10)
    """
    start_time = time.time()

    try:
        # Build query based on tags
        query = {"tags": {"$all": tags}} if tags else {}
        
        # Execute query with pagination
        cursor = db.fields.find(query).skip(skip).limit(limit)
        fields = list(cursor)
        
        # Convert ObjectIds to strings
        for field in fields:
            field['_id'] = str(field['_id'])
        
        # Convert to Pydantic models
        result_data = [FieldModel(**field) for field in fields]
        
        # Get total count
        result_count = db.fields.count_documents(query)
        
    except Exception as e:
        logger.error(f"Failed to retrieve fields: {e}")
        raise ValueError("Failed to retrieve fields")

    elapsed_time = time.time() - start_time

    return {
        "ResultCount": result_count,
        "PageSize": limit,
        "ResultData": [field.model_dump() for field in result_data],
        "Metrics": {
            "ElapsedTime": elapsed_time
        }
    }