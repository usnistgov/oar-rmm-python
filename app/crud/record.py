import time
from app.crud.base import BaseCRUD
from app.config import settings
import logging
import re
from app.middleware.request_processor import ProcessRequest
from app.middleware.exceptions import (
    InternalServerException,
    ResourceNotFoundException,
    KeyWordNotFoundException,
    IllegalArgumentException,
)

logger = logging.getLogger(__name__)

class RecordCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(settings.RECORDS_COLLECTION)

    def get(self, record_id: str) -> dict:
        """Get a single record by @ID, EDIID, or ARK identifier"""
        start_time = time.time()
        print('Getting record with ID:', record_id)
        try:
            # URL decode the record_id (convert %3A back to :)
            from urllib.parse import unquote
            decoded_id = unquote(record_id)
            
            # Build query conditions similar to metrics lookup
            query_conditions = [
                {"ediid": decoded_id},
                {"@id": decoded_id}
            ]
            
            # If the ID doesn't start with "ark:", try additional patterns
            if not decoded_id.startswith("ark:"):
                query_conditions.extend([
                    {"@id": f"ark:{decoded_id}"},  # Try with ark: prefix
                    {"ediid": {"$regex": f".*{re.escape(decoded_id)}$"}},  # Match at end of ediid
                    {"@id": {"$regex": f".*{re.escape(decoded_id)}$"}}     # Match at end of @id
                ])
            
            # Execute the query
            query_result = self.collection.find_one(
                {"$or": query_conditions},
                {"_id": 0}  # Use dict format for projection
            )
            
            if query_result:
                return {
                    "ResultCount": 1,
                    "ResultData": [query_result],
                    "Metrics": {"ElapsedTime": time.time() - start_time}
                }

            raise ResourceNotFoundException(f"Record with ID {decoded_id} not found")
                    
        except ResourceNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving record: {e}")
            raise InternalServerException(f"Failed to retrieve record: {str(e)}")
        
    def get_all(self, skip: int = 0, limit: int = 10) -> dict:
        """
        Get multiple records with pagination.
        
        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            
        Returns:
            dict: The records data with metrics
        """
        return super().get_all(skip, limit)
        
    def search(self, **kwargs) -> dict:
        """
        Search records and return paginated results plus pre-computed facet counts
        (topics, resourceTypes, components, authors, keywords) in a single MongoDB
        aggregation round-trip, eliminating the need for a separate filters request.
        """
        start_time = time.time()
        try:
            processor = ProcessRequest()
            try:
                processed = processor.process_search_params(kwargs)
                if "projection" not in processed:
                    processed["projection"] = {}
                processed["projection"]["_id"] = 0
            except Exception as e:
                logger.error(f"Error processing search parameters: {e}")
                raise IllegalArgumentException(str(e))

            query = processed["query"]
            projection = processed.get("projection", {"_id": 0})
            skip = processed.get("skip") or 0
            limit = processed.get("limit") or 0
            sort_spec = processed.get("sort") or []

            # Sub-pipeline that returns the requested page of documents
            data_pipeline: list = []
            if sort_spec:
                data_pipeline.append({"$sort": {f: d for f, d in sort_spec}})
            if skip:
                data_pipeline.append({"$skip": skip})
            if limit:
                data_pipeline.append({"$limit": limit})
            data_pipeline.append({"$project": projection})

            pipeline = [
                {"$match": query},
                {"$facet": {
                    # Paginated result set
                    "data": data_pipeline,
                    # Total matched count (unpaginated)
                    "total": [{"$count": "count"}],
                    # Research topics (topic[].tag)
                    "topics": [
                        {"$unwind": {"path": "$topic", "preserveNullAndEmptyArrays": False}},
                        {"$group": {"_id": "$topic.tag", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ],
                    # Record @type values (e.g. "nrdp:DataPublication")
                    "resourceTypes": [
                        {"$unwind": {"path": "$@type", "preserveNullAndEmptyArrays": False}},
                        {"$group": {"_id": "$@type", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ],
                    # Component types (components[].@type, nrdp-prefixed only)
                    "components": [
                        {"$unwind": {"path": "$components", "preserveNullAndEmptyArrays": False}},
                        {"$unwind": {"path": "$components.@type", "preserveNullAndEmptyArrays": False}},
                        {"$match": {"components.@type": {"$regex": "nrdp", "$options": "i"}}},
                        {"$group": {"_id": "$components.@type", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ],
                    # Authors / contributors (contactPoint.fn)
                    "authors": [
                        {"$match": {"contactPoint.fn": {"$exists": True, "$nin": [None, ""]}}},
                        {"$group": {"_id": "$contactPoint.fn", "count": {"$sum": 1}}},
                        {"$sort": {"_id": 1}},
                    ],
                    # Keywords
                    "keywords": [
                        {"$unwind": {"path": "$keyword", "preserveNullAndEmptyArrays": False}},
                        {"$group": {"_id": "$keyword", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ],
                }},
            ]

            # Preserve collation used by the cursor-based search for consistent sorting
            agg_kwargs: dict = {}
            if sort_spec:
                agg_kwargs["collation"] = {
                    "locale": "en",
                    "strength": 3,
                    "numericOrdering": True,
                    "caseLevel": True,
                    "alternate": "shifted",
                }

            logger.info(f"Record search query: {query}")
            result = list(self.collection.aggregate(pipeline, **agg_kwargs))

            empty_facets = {
                "topics": [], "resourceTypes": [], "components": [],
                "authors": [], "keywords": [],
            }

            if not result:
                return {
                    "ResultCount": 0, "ResultData": [], "PageSize": limit,
                    "Facets": empty_facets,
                    "Metrics": {"ElapsedTime": time.time() - start_time},
                }

            bucket = result[0]
            docs = bucket.get("data", [])
            total_list = bucket.get("total", [])
            total = total_list[0]["count"] if total_list else 0

            facets = {
                "topics": [
                    {"tag": item["_id"], "count": item["count"]}
                    for item in bucket.get("topics", []) if item.get("_id")
                ],
                "resourceTypes": [
                    {"type": item["_id"], "count": item["count"]}
                    for item in bucket.get("resourceTypes", []) if item.get("_id")
                ],
                "components": [
                    {"type": item["_id"], "count": item["count"]}
                    for item in bucket.get("components", []) if item.get("_id")
                ],
                "authors": [
                    {"name": item["_id"], "count": item["count"]}
                    for item in bucket.get("authors", []) if item.get("_id")
                ],
                "keywords": [
                    {"keyword": item["_id"], "count": item["count"]}
                    for item in bucket.get("keywords", []) if item.get("_id")
                ],
            }

            logger.info(f"Record search returned {total} total, {len(docs)} in page")
            return {
                "ResultCount": total,
                "ResultData": docs,
                "PageSize": limit,
                "Facets": facets,
                "Metrics": {"ElapsedTime": time.time() - start_time},
            }

        except (KeyWordNotFoundException, IllegalArgumentException):
            raise
        except Exception as e:
            logger.error(f"Record search failed: {e}")
            raise InternalServerException(f"Failed to search records: {str(e)}")

# Create singleton instance
record_crud = RecordCRUD()