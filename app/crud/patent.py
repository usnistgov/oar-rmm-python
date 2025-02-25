from app.crud.base import BaseCRUD
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PatentCRUD(BaseCRUD):
    def __init__(self):
        """Initialize patents collection"""
        super().__init__("patents")
        
    def create(self, data: dict) -> dict:
        """
        Create a new patent in the database.
        
        Args:
            data (dict): The patent data to create
            
        Returns:
            dict: The newly created patent with metrics
        """
        return super().create(data)

    def get(self, patent_id: str) -> dict:
        """
        Get a single patent by ID or patent number.
        
        Args:
            patent_id (str): The ID or patent number to retrieve
            
        Returns:
            dict: The patent data with metrics
        """
        # Try getting by MongoDB ID first
        try:
            return super().get(patent_id)
        except:
            # If not found, try by Patent #
            result = self.search(**{"Patent #": patent_id})
            if result["ResultCount"] > 0:
                return {
                    "ResultData": result["ResultData"][0],
                    "ResultCount": 1,
                    "Metrics": result["Metrics"]
                }
            raise ValueError("Patent not found")

    def search(self, **kwargs) -> dict:
        """
        Search patents with various criteria.
        
        Args:
            **kwargs: Search parameters including:
                - searchphrase (Optional[str]): Text to search for
                - skip (int): Number of items to skip
                - limit (int): Maximum items to return
                - sort_asc (Optional[List[str]]): Fields to sort ascending
                - sort_desc (Optional[List[str]]): Fields to sort descending
                - include (Optional[List[str]]): Fields to include
                - exclude (Optional[List[str]]): Fields to exclude
                - Laboratory 1 (Optional[str]): Filter by laboratory
                - Status (Optional[str]): Filter by status
                - File Date (Optional[str]): Filter by file date
            
        Returns:
            dict: Search results with metrics
        """
        return super().search(**kwargs)

# Create singleton instance
patent_crud = PatentCRUD()