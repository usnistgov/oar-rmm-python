from typing import Dict, Any
from app.crud.base import BaseCRUD
import logging

logger = logging.getLogger(__name__)

class TaxonomyCRUD(BaseCRUD):
    def __init__(self):
        """Initialize taxonomy collection"""
        super().__init__("taxonomy")
        
    def create(self, data: dict) -> dict:
        """
        Create a new taxonomy entry in the database.
        
        Args:
            data (dict): The taxonomy data to create
            
        Returns:
            dict: The newly created taxonomy with metrics
        """
        return super().create(data)

    def get(self, taxonomy_id: str) -> dict:
        """
        Get a single taxonomy entry by ID.
        
        Args:
            taxonomy_id (str): The ID of the taxonomy to retrieve
            
        Returns:
            dict: The taxonomy data with metrics
        """
        return super().get(taxonomy_id)
        
    def search(self, **kwargs) -> dict:
        """
        Search taxonomies based on parameters.
        
        Args:
            **kwargs: Search parameters
            
        Returns:
            dict: Search results with metrics
        """
        return super().search(**kwargs)

# Create a singleton instance
taxonomy_crud = TaxonomyCRUD()