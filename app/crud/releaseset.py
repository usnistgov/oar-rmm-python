from typing import Dict, Any
from app.crud.base import BaseCRUD
import logging

logger = logging.getLogger(__name__)

class ReleaseSetCRUD(BaseCRUD):
    def __init__(self):
        """Initialize releasesets collection"""
        super().__init__("releasesets")
        
    def create(self, data: dict) -> dict:
        """
        Create a new release set entry in the database.
        
        Args:
            data (dict): The release set data to create
            
        Returns:
            dict: The newly created release set with metrics
        """
        return super().create(data)

    def get(self, releaseset_id: str) -> dict:
        """
        Get a single release set entry by ID.
        
        Args:
            releaseset_id (str): The ID of the release set to retrieve
            
        Returns:
            dict: The release set data with metrics
        """
        return super().get(releaseset_id)
        
    def search(self, **kwargs) -> dict:
        """
        Search release sets based on parameters.
        
        Args:
            **kwargs: Search parameters
            
        Returns:
            dict: Search results with metrics
        """
        return super().search(**kwargs)

# Create a singleton instance
releaseset_crud = ReleaseSetCRUD()