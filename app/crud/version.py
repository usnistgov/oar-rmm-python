from typing import Dict, Any
from app.crud.base import BaseCRUD
import logging
from app.config import settings
logger = logging.getLogger(__name__)

class VersionCRUD(BaseCRUD):
    def __init__(self):
        """Initialize versions collection"""
        super().__init__(settings.VERSIONS_COLLECTION)
        
    def create(self, data: dict) -> dict:
        """
        Create a new version entry in the database.
        
        Args:
            data (dict): The version data to create
            
        Returns:
            dict: The newly created version with metrics
        """
        return super().create(data)

    def get(self, version_id: str) -> dict:
        """
        Get a single version entry by ID.
        
        Args:
            version_id (str): The ID of the version to retrieve
            
        Returns:
            dict: The version data with metrics
        """
        return super().get(version_id)
        
    def search(self, **kwargs) -> dict:
        """
        Search versions based on parameters.
        
        Args:
            **kwargs: Search parameters
            
        Returns:
            dict: Search results with metrics
        """
        return super().search(**kwargs)

# Create a singleton instance
version_crud = VersionCRUD()