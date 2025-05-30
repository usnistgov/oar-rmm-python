import time
from app.crud.base import BaseCRUD
from app.config import settings
import logging

from app.middleware.exceptions import InternalServerException, ResourceNotFoundException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecordCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(settings.RECORDS_COLLECTION)

    def get(self, record_id: str) -> dict:
        """Get a single record by @ID, EDIID, or ARK identifier"""
        start_time = time.time()
        try:
            # URL decode the record_id (convert %3A back to :)
            from urllib.parse import unquote
            decoded_id = unquote(record_id)
            
            # Try to find by any of the supported identifiers
            query_result = self.collection.find_one({
                "$or": [
                    {"ediid": decoded_id},  # Try as EDIID
                    {"@id": decoded_id},  # Try as ARK ID
                    {"@id": f"ark:{decoded_id.split('ark:')[1]}" if "ark:" in decoded_id else decoded_id}  # Handle ark: prefix variations
                ]
                },
                projection={"_id": 0}  # Exclude _id
            )
            
            if query_result:
                query_result["@id"] = str(query_result["@id"])
                return {
                    "ResultData": [query_result],
                    "ResultCount": 1,
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
        Search for records with various criteria.
        
        Args:
            **kwargs: Search parameters
            
        Returns:
            dict: Search results with metrics
        """
        return super().search(**kwargs)

# Create singleton instance
record_crud = RecordCRUD()