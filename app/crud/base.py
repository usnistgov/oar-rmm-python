from typing import Dict, Any, List, Optional
from bson.objectid import ObjectId
from app.database import db
import time
import logging

logger = logging.getLogger(__name__)

class BaseCRUD:
    def __init__(self, collection_name: str):
        self.collection = db[collection_name]

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
        
    def search(
        self,
        searchphrase: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
        sort_asc: Optional[List[str]] = None,
        sort_desc: Optional[List[str]] = None,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        logical_op: str = "AND",
        **field_queries: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generic search function"""
        start_time = time.time()
        
        try:
            # Build query
            query = {}
            
            if searchphrase:
                if searchphrase.startswith('"') and searchphrase.endswith('"'):
                    phrase = searchphrase[1:-1]
                    query["$text"] = {"$search": f"\"{phrase}\""}
                else:
                    query["$text"] = {"$search": searchphrase}

            # Handle field queries
            field_conditions = []
            for field, value in field_queries.items():
                if isinstance(value, str) and ',' in value:
                    values = [v.strip() for v in value.split(',')]
                    field_conditions.append({field: {"$in": values}})
                else:
                    field_conditions.append({field: value})

            if field_conditions:
                if len(field_conditions) > 1:
                    query[f"${logical_op.lower()}"] = field_conditions
                else:
                    query.update(field_conditions[0])

            # Projection
            projection = {}
            if include:
                projection.update({field: 1 for field in include})
            if exclude:
                projection.update({field: 0 for field in exclude})

            # Sorting
            sort_params = []
            if sort_asc:
                sort_params.extend((field, 1) for field in sort_asc)
            if sort_desc:
                sort_params.extend((field, -1) for field in sort_desc)

            # Execute query
            cursor = self.collection.find(
                filter=query,
                projection=projection if projection else None
            ).skip(skip).limit(limit)

            if sort_params:
                cursor = cursor.sort(sort_params)

            # Process results
            docs = list(cursor)
            for doc in docs:
                doc["_id"] = str(doc["_id"])

            result_count = self.collection.count_documents(query)

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise ValueError(f"Failed to search documents: {e}")

        return {
            "Metrics": {"ElapsedTime": time.time() - start_time},
            "ResultCount": result_count,
            "PageSize": limit,
            "ResultData": docs
        }