from app.crud.base import BaseCRUD
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecordCRUD(BaseCRUD):
    def __init__(self):
        super().__init__(settings.RECORDS_COLLECTION)
        
        
    def create(self, data: dict) -> dict:
        """
        Create a new record in the database.
        
        Args:
            data (dict): The record data to create
            
        Returns:
            dict: The newly created record
        """
        return super().create(data)

    def get(self, record_id: str) -> dict:
        """
        Get a single record by ID or ediid.
        
        Args:
            record_id (str): The ID or ediid of the record to retrieve
                
        Returns:
            dict: The record data without wrapper
        """
        try:
            # First try to get by ObjectId
            try:
                from bson.objectid import ObjectId
                # See if it's a valid ObjectId
                if len(record_id) == 24 and all(c in '0123456789abcdefABCDEF' for c in record_id):
                    result = super().get(record_id)
                    if result and "ResultData" in result and result["ResultData"]:
                        return result["ResultData"][0]  # Return just the record
            except Exception as e:
                logger.debug(f"Not an ObjectId, trying ediid: {e}")
                
            # Try to find by ediid
            query_result = self.collection.find_one({"ediid": record_id})
            if query_result:
                # Convert _id to string
                query_result["_id"] = str(query_result["_id"])
                return query_result  # Return just the record
                
            # If we got here, record wasn't found
            from app.middleware.exceptions import ResourceNotFoundException
            raise ResourceNotFoundException(f"Record with ID/ediid {record_id} not found")
        except Exception as e:
            if "ResourceNotFoundException" in str(type(e)):
                raise
            logger.error(f"Error retrieving record: {e}")
            from app.middleware.exceptions import InternalServerException
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