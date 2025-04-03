from app.config import settings
from typing import Dict, Any
from app.crud.base import BaseCRUD
import logging

logger = logging.getLogger(__name__)

class TaxonomyCRUD(BaseCRUD):
    def __init__(self):
        """Initialize taxonomy collection"""
        super().__init__(settings.TAXONOMY_COLLECTION)
        
    def create(self, data: dict) -> dict:
        """Create a new taxonomy entry in the database."""
        return super().create(data)

    def get(self, taxonomy_id: str) -> dict:
        """Get a single taxonomy entry by ID."""
        base_result = super().get(taxonomy_id)
        return base_result.get("ResultData", [{}])[0]  # Return just the document
        
    def search(self, **kwargs) -> list:
        """Search taxonomies based on parameters."""
        base_result = super().search(**kwargs)
        return base_result.get("ResultData", [])  # Return just the list of documents

# Create a singleton instance
taxonomy_crud = TaxonomyCRUD()