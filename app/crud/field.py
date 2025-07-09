from app.crud.base import BaseCRUD
from app.config import settings

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FieldCRUD(BaseCRUD):
    def __init__(self):
            super().__init__(settings.FIELDS_COLLECTION)
        
    def create(self, data: dict) -> dict:
        """
        Create a new field in the database.
        
        Args:
            data (dict): The field data to create
            
        Returns:
            dict: The newly created field with the following structure:
                {
                    "ResultCount": 1,
                    "ResultData": [field_dict],
                    "Metrics": {"ElapsedTime": float}
                }
                
        Raises:
            ValueError: If field creation fails
        """
        return super().create(data)

    def get(self, field_id: str) -> dict:
        """
        Get a single field by ID.
        
        Args:
            field_id (str): The ID of the field to retrieve
            
        Returns:
            dict: The field data with the following structure:
                {
                    "ResultData": [field_dict],
                    "ResultCount": 1,
                    "Metrics": {"ElapsedTime": float}
                }
                
        Raises:
            ValueError: If field is not found or retrieval fails
        """
        return super().get(field_id)
        
    def get_all(self, skip: int = 0, limit: int = 10) -> dict:
        """
        Get multiple fields with pagination.
        
        Args:
            skip (int): Number of fields to skip (default: 0)
            limit (int): Maximum number of fields to return (default: 10)
            
        Returns:
            dict: The fields data with the following structure:
                {
                    "ResultData": [field_dict, ...],
                    "ResultCount": int,
                    "PageSize": int,
                    "Metrics": {"ElapsedTime": float}
                }
                
        Raises:
            ValueError: If retrieval fails
        """
        base_result = super().get_all(skip, limit)
        return base_result.get("ResultData", [])
        
    def search(self, **kwargs) -> dict:
        """
        Search for fields with various criteria.
        
        Args:
            **kwargs: Search parameters including:
                - searchphrase (Optional[str]): Text to search for
                - skip (int): Number of records to skip (default: 0)
                - limit (int): Maximum records to return (default: 10)
                - sort_asc (Optional[List[str]]): Fields to sort ascending
                - sort_desc (Optional[List[str]]): Fields to sort descending
                - include (Optional[List[str]]): Fields to include
                - exclude (Optional[List[str]]): Fields to exclude
                - logical_op (str): Logical operator for conditions ("AND"/"OR")
                - Additional field-specific filters
            
        Returns:
            dict: Search results with the following structure:
                {
                    "ResultData": [field_dict, ...],
                    "ResultCount": int,
                    "PageSize": int,
                    "Metrics": {"ElapsedTime": float}
                }
                
        Raises:
            ValueError: If search fails
        """
        base_result = super().search(**kwargs)
        return base_result.get("ResultData", [])

# Create singleton instance
field_crud = FieldCRUD()