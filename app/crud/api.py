from typing import Dict, Any
from app.crud.base import BaseCRUD
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class ApiCRUD(BaseCRUD):
    def __init__(self):
        """Initialize APIs collection"""
        super().__init__(settings.RESOURCES_COLLECTION)
        
    # def create(self, data: dict) -> dict:
    #     """
    #     Create a new API entry in the database.
        
    #     Args:
    #         data (dict): The API data to create
            
    #     Returns:
    #         dict: The newly created API with metrics
    #     """
    #     return super().create(data)

    def get(self, api_id: str) -> dict:
        """
        Get a single API entry by ID.
        
        Args:
            api_id (str): The ID of the API to retrieve
            
        Returns:
            dict: The API data with metrics
        """
        return super().get(api_id)
        
    def search(self, **kwargs) -> dict:
        """
        Search APIs based on parameters.
        
        Args:
            **kwargs: Search parameters
            
        Returns:
            dict: Search results with metrics
        """
        return super().search(**kwargs)

# Create a singleton instance
api_crud = ApiCRUD()