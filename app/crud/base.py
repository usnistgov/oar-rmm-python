from app.middleware.request_processor import ProcessRequest
from app.middleware.exceptions import ResourceNotFoundException, InternalServerException, KeyWordNotFoundException, IllegalArgumentException
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
            raise InternalServerException(f"Failed to create document: {str(e)}")

    def get(self, doc_id: str) -> Dict[str, Any]:
        """Get a single document by ID"""
        start_time = time.time()
        try:
            doc = self.collection.find_one({"_id": ObjectId(doc_id)})
            if not doc:
                raise ResourceNotFoundException(f"Document with ID {doc_id} not found")
            doc["_id"] = str(doc["_id"])
            return {
                "ResultData": [doc],
                "ResultCount": 1,
                "Metrics": {"ElapsedTime": time.time() - start_time}
            }
        except ResourceNotFoundException as e:
            logger.error(f"Document not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve document: {e}")
            raise InternalServerException(f"Failed to retrieve document: {str(e)}")

    def get_all(self, skip: int = 0, limit: int = 10, **filters) -> Dict[str, Any]:
        """Get all documents with optional filtering"""
        start_time = time.time()
        try:
            cursor = self.collection.find(filters).skip(skip).limit(limit)
            docs = list(cursor)
            
            if not docs:
                raise KeyWordNotFoundException("No documents found matching the criteria")
                
            for doc in docs:
                doc["_id"] = str(doc["_id"])
            
            count = self.collection.count_documents(filters)
            
            return {
                "ResultData": docs,
                "ResultCount": count,
                "PageSize": limit,
                "Metrics": {"ElapsedTime": time.time() - start_time}
            }
        except KeyWordNotFoundException as e:
            logger.error(f"No documents found: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            raise InternalServerException(f"Failed to retrieve documents: {str(e)}")
        
    def search(self, **kwargs) -> Dict[str, Any]:
        """Generic search function"""
        start_time = time.time()
        try:
            # Create new request processor instance for each search
            self.request_processor = ProcessRequest()
            
            # Log collection being searched
            logger.info(f"Searching collection: {self.collection.name}")
            
            # Process request parameters
            try:
                processed = self.request_processor.process_search_params(kwargs)
            except Exception as e:
                # If there's an error processing the search parameters, it's likely an illegal argument
                logger.error(f"Error processing search parameters: {e}")
                raise IllegalArgumentException(str(e))
            
            logger.info(f"Search parameters: {kwargs}")
            logger.info(f"Processed query: {processed}")

            # Check if collection exists and has documents
            if self.collection.count_documents({}) == 0:
                logger.warning(f"Collection {self.collection.name} is empty")
                raise KeyWordNotFoundException(f"No documents found in {self.collection.name} collection")

            try:
                # Using explicit parameters to catch any issues
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

                # Get results - convert cursor to list to materialize any errors
                docs = list(cursor)
                logger.info(f"Found {len(docs)} documents")
            except Exception as e:
                logger.error(f"MongoDB query execution error: {e}")
                raise InternalServerException(f"Error executing MongoDB query: {str(e)}")
            
            if not docs:
                raise KeyWordNotFoundException("No documents found matching the search criteria")
                
            for doc in docs:
                doc["_id"] = str(doc["_id"])

            count = self.collection.count_documents(processed["query"])
            
            return {
                "ResultData": docs,
                "ResultCount": count,
                "PageSize": processed["limit"],
                "Metrics": {"ElapsedTime": time.time() - start_time}
            }
        except KeyWordNotFoundException as e:
            logger.error(f"No search results: {e}")
            raise
        except IllegalArgumentException as e:
            logger.error(f"Invalid search parameters: {e}")
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise InternalServerException(f"Failed to search documents: {str(e)}")