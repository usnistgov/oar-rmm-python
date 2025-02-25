from app.middleware.request_processor import ProcessRequest
from typing import Dict, Any, List, Optional
from bson.objectid import ObjectId
from app.database import db
import time
import logging

logger = logging.getLogger(__name__)

class BaseCRUD:
    def __init__(self, collection_name: str):
        self.collection = db[collection_name]
        self.request_processor = ProcessRequest()


    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document"""
        try:
            result = self.collection.insert_one(data)
            new_doc = self.collection.find_one({"_id": result.inserted_id})
            new_doc["_id"] = str(new_doc["_id"])
            return {
                "ResultData": [new_doc],
                "ResultCount": 1,
                "Metrics": {"ElapsedTime": 0}
            }
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise ValueError("Failed to create document")

    def get(self, doc_id: str) -> Dict[str, Any]:
        """Get a single document by ID"""
        start_time = time.time()
        try:
            doc = self.collection.find_one({"_id": ObjectId(doc_id)})
            if not doc:
                raise ValueError("Document not found")
            doc["_id"] = str(doc["_id"])
            return {
                "ResultData": [doc],
                "ResultCount": 1,
                "Metrics": {"ElapsedTime": time.time() - start_time}
            }
        except Exception as e:
            logger.error(f"Failed to retrieve document: {e}")
            raise ValueError("Failed to retrieve document")

    def get_all(self, skip: int = 0, limit: int = 10, **filters) -> Dict[str, Any]:
        """Get all documents with optional filtering"""
        start_time = time.time()
        try:
            cursor = self.collection.find(filters).skip(skip).limit(limit)
            docs = list(cursor)
            for doc in docs:
                doc["_id"] = str(doc["_id"])
            
            count = self.collection.count_documents(filters)
            
            return {
                "ResultData": docs,
                "ResultCount": count,
                "PageSize": limit,
                "Metrics": {"ElapsedTime": time.time() - start_time}
            }
        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            raise ValueError("Failed to retrieve documents")
        
    def search(self, **kwargs) -> Dict[str, Any]:
        """Generic search function"""
        start_time = time.time()
        try:
            # Create new request processor instance for each search
            self.request_processor = ProcessRequest()
            
            # Process request parameters
            processed = self.request_processor.process_search_params(kwargs)
            
            logger.info(f"Search parameters: {kwargs}")
            logger.info(f"Processed query: {processed}")

            # Execute query with processed parameters
            cursor = self.collection.find(
                filter=processed["query"],
                projection=processed["projection"]
            )

            if processed["skip"]:
                cursor = cursor.skip(processed["skip"])
            
            if processed["limit"]:
                cursor = cursor.limit(processed["limit"])

            if processed["sort"]:
                cursor = cursor.sort(processed["sort"])

            # Get results
            docs = list(cursor)
            logger.info(f"Found {len(docs)} documents")
            
            for doc in docs:
                doc["_id"] = str(doc["_id"])

            count = self.collection.count_documents(processed["query"])
            
            return {
                "ResultData": docs,
                "ResultCount": count,
                "PageSize": processed["limit"],
                "Metrics": {"ElapsedTime": time.time() - start_time}
            }

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise ValueError(f"Failed to search documents: {e}")