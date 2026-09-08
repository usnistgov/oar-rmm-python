"""CRUD operations for the "patents" resource collection.

Catalogs NIST patents (imported from a static JSON export via
``app.scripts.populate_patents``), served at ``/patents``. Uses a hard-coded
collection name (``"patents"``).
"""
from app.crud.base import BaseCRUD
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PatentCRUD(BaseCRUD):
    """CRUD operations bound to the ``patents`` collection."""

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
        """Get a single patent by MongoDB ID or patent number.

        First attempts a MongoDB ``_id`` lookup via :meth:`BaseCRUD.get`. If
        that fails, falls back to searching by the ``"Patent #"`` field.

        Args:
            patent_id: A MongoDB ``_id`` string or a patent number.

        Returns:
            dict: ``{"ResultCount": 1, "ResultData": doc, "Metrics": {...}}``.

        Raises:
            ValueError: If no patent matches either the ID or patent number.
        """
        # Try getting by MongoDB ID first
        try:
            return super().get(patent_id)
        except:
            # If not found, try by Patent #
            result = self.search(**{"Patent #": patent_id})
            if result["ResultCount"] > 0:
                return {

                    "ResultCount": 1,
                    "ResultData": result["ResultData"][0],
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