from app.crud.base import BaseCRUD
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecordCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("records")
        
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
        Get a single record by ID.
        
        Args:
            record_id (str): The ID of the record to retrieve
            
        Returns:
            dict: The record data with metrics
        """
        return super().get(record_id)
        
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