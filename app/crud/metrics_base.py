from typing import Dict, Any, Optional, List
import time
from datetime import datetime
from bson import ObjectId
from app.database import metrics_db
from app.middleware.exceptions import ResourceNotFoundException
from app.middleware.request_processor import ProcessRequest
from pymongo import ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)

class MetricsBaseCRUD:
    def __init__(self):
        """Initialize metrics base functionality"""
        self.request_processor = ProcessRequest()
    
    def process_metrics_query(self, collection, params: Dict[str, Any], collection_name: str) -> Dict[str, Any]:
        """
        Process input parameters and retrieve metrics data
        
        Args:
            collection: MongoDB collection to query
            params: Query parameters
            collection_name: Name of the collection/metrics type
            
        Returns:
            Dict with metrics results
        """
        start_time = datetime.now()
        
        # Make a copy of params to avoid modifying the original
        params_copy = params.copy() if params else {}
        
        # Handle include/exclude parameters
        if "include" in params_copy:
            del params_copy["include"]
        if "exclude" in params_copy:
            del params_copy["exclude"]
            
        # Always exclude _id and ip_list fields for privacy
        params_copy["exclude"] = "_id,ip_list"
        
        # Process the search parameters to build MongoDB query
        request = self.request_processor
        request.reset_state()
        query_data = request.process_search_params(params_copy)
        
        # Get count of total matching documents
        count = collection.count_documents(query_data["query"])
        
        # Fix sort parameter - handle None or empty sort
        sort_param = query_data.get("sort")
        if not sort_param or (isinstance(sort_param, list) and len(sort_param) == 0):
            # Default sort by last_time_logged if available
            cursor = collection.find(
                query_data["query"],
                query_data["projection"]
            ).sort([("last_time_logged", DESCENDING)]).skip(query_data["skip"]).limit(query_data["limit"])
        else:
            # Use provided sort
            cursor = collection.find(
                query_data["query"],
                query_data["projection"]
            ).sort(sort_param).skip(query_data["skip"]).limit(query_data["limit"])
        
        # Convert to list and handle ObjectIDs
        results = []
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            results.append(doc)
            
        result_doc = {
            f"{collection_name}Count": count,
            "PageSize": query_data["limit"]
        }
        
        # For TotalUsers, only return the count
        if collection_name.lower() == "totalusers":
            return result_doc
            
        # Add the metrics data
        result_doc[collection_name] = results
        result_doc["Metrics"] = {
            "ElapsedTime": (datetime.now() - start_time).total_seconds()
        }
        
        return result_doc
    
    # Keep existing methods for single-collection operations
    def create(self, collection, data: dict) -> dict:
        """
        Create a new document in the specified collection.
        
        Args:
            collection: MongoDB collection to insert into
            data (dict): The document data to insert
            
        Returns:
            dict: The created document with metadata
        """
        start_time = time.time()
        
        # Add creation timestamp if not present
        if "timestamp" not in data:
            data["timestamp"] = datetime.utcnow().isoformat()
        
        # Insert the document
        result = collection.insert_one(data)
        
        # Return the created document with metrics
        return {
            "ResultData": {
                "_id": str(result.inserted_id),
                **data
            },
            "Metrics": {
                "ElapsedTime": time.time() - start_time
            }
        }