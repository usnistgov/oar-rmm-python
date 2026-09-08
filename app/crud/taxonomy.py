"""CRUD operations for the "taxonomy" resource collection.

Holds the hierarchical topic/subject taxonomy used to classify records (e.g.
for the ``topic.tag`` faceting logic in ``app.crud.record``), served at
``/taxonomy``. This module is a thin wrapper around
:class:`~app.crud.base.BaseCRUD` that unwraps the standard result envelope
into bare documents/lists for its callers.
"""
from app.config import settings
from typing import Dict, Any
from app.crud.base import BaseCRUD
import logging

logger = logging.getLogger(__name__)

class TaxonomyCRUD(BaseCRUD):
    """CRUD operations bound to the taxonomy collection (``settings.TAXONOMY_COLLECTION``)."""

    def __init__(self):
        """Initialize taxonomy collection"""
        super().__init__(settings.TAXONOMY_COLLECTION)
        
    def create(self, data: dict) -> dict:
        """Create a new taxonomy entry in the database.

        Args:
            data: The taxonomy document to insert.

        Returns:
            dict: The result envelope from :meth:`BaseCRUD.create`.
        """
        return super().create(data)

    def get(self, taxonomy_id: str) -> dict:
        """Get a single taxonomy entry by ID.

        Args:
            taxonomy_id: String form of the document's MongoDB ``_id``.

        Returns:
            dict: The bare taxonomy document (unwrapped from the result
            envelope), or ``{}`` if the envelope had no ``ResultData``.

        Raises:
            ResourceNotFoundException: If no taxonomy entry with that ID exists.
        """
        base_result = super().get(taxonomy_id)
        return base_result.get("ResultData", [{}])[0]  # Return just the document
        
    def search(self, **kwargs) -> list:
        """Search taxonomies based on parameters.

        Args:
            **kwargs: Search parameters forwarded to :meth:`BaseCRUD.search`.

        Returns:
            list: The matching taxonomy documents (unwrapped from the result
            envelope); empty list if none match.
        """
        base_result = super().search(**kwargs)
        return base_result.get("ResultData", [])  # Return just the list of documents

# Create a singleton instance
taxonomy_crud = TaxonomyCRUD()