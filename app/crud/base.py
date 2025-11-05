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

    def get(self, doc_id: str) -> Dict[str, Any]:
        """Get a single document by ID"""
        print(f"Getting document with ID: {doc_id}")
        start_time = time.time()
        try:
            doc = self.collection.find_one({"_id": ObjectId(doc_id)})
            if not doc:
                raise ResourceNotFoundException(f"Document with ID {doc_id} not found")
            doc["_id"] = str(doc["_id"])
            return {
                "ResultCount": 1,
                "ResultData": [doc],
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
            cursor = self.collection.find(
                filter=filters,
                projection={"_id": 0}
            ).skip(skip)
            
            # Only apply limit if it's greater than 0 (0 means return all)
            if limit > 0:
                cursor = cursor.limit(limit)
            
            docs = list(cursor)
            
            if not docs:
                raise KeyWordNotFoundException("No documents found matching the criteria")
            
            count = self.collection.count_documents(filters)
            
            return {
                "ResultCount": count,
                "ResultData": docs,
                "PageSize": limit if limit > 0 else 0,  # 0 indicates all results returned
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
                # Ensure _id is excluded from projection
                if "projection" not in processed:
                    processed["projection"] = {}
                processed["projection"]["_id"] = 0
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

                # Only apply skip if it's greater than 0
                if processed["skip"] and processed["skip"] > 0:
                    cursor = cursor.skip(processed["skip"])
                
                # Only apply limit if it's specified and greater than 0 (None or 0 means return all results)
                if processed["limit"] is not None and processed["limit"] > 0:
                    cursor = cursor.limit(processed["limit"])

                if processed["sort"] and isinstance(processed["sort"], list) and len(processed["sort"]) > 0:
                    # For nullable fields like firstIssued/annotated, we need to handle nulls last
                    sort_spec = []
                    for field, direction in processed["sort"]:
                        # Check if this is a nullable field that should sort nulls last
                        if field in ["firstIssued", "annotated"]:
                            # First sort by whether the field exists
                            sort_spec.append((f"{field}", direction))
                        else:
                            sort_spec.append((field, direction))
                            
                    cursor = cursor.sort(sort_spec)
                    cursor = cursor.collation({
                        "locale": "en",
                        "strength": 3,  # 3 for case+symbol sensitivity
                        "numericOrdering": True,  # Properly handle numeric parts
                        "caseLevel": True,  # Ensure proper case handling
                        "alternate": "shifted"  # Ignore punctuation/symbols in base comparison
                    })
                elif "sort_asc" in kwargs or "sort_desc" in kwargs:
                    logger.warning(f"Sort requested but not properly processed. Processed sort: {processed['sort']}")
                # Get results - convert cursor to list to materialize any errors
                docs = list(cursor)
                logger.info(f"Found {len(docs)} documents")
            except Exception as e:
                logger.error(f"MongoDB query execution error: {e}")
                raise InternalServerException(f"Error executing MongoDB query: {str(e)}")
            
            if not docs:
                # raise KeyWordNotFoundException("No documents found matching the search criteria")
                # MARK: @Mehdi: Instead of raising an exception, return an empty result set to match current
                # implementation behavior
                logger.warning("No documents found matching the search criteria")
                return {
                    "ResultCount": 0,
                    "ResultData": [],
                    "PageSize": processed["limit"] if processed["limit"] is not None else 0,
                    "Metrics": {"ElapsedTime": time.time() - start_time}
                }
                
            for doc in docs:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])

            # Get total count of matching documents
            count = self.collection.count_documents(processed["query"])
            
            # Determine PageSize based on whether pagination was used
            page_size = processed["limit"] if processed["limit"] is not None and processed["limit"] > 0 else 0
            
            return {

                "ResultCount": count,
                "ResultData": docs,
                "PageSize": page_size,  # 0 indicates all results returned
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