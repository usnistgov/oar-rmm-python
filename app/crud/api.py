"""CRUD operations for the "APIs" resource collection.

The APIs collection catalogs external/internal API endpoints exposed by the
Public Data Repository ecosystem (served at ``/apis``). This module is a thin
wrapper around :class:`~app.crud.base.BaseCRUD` that unwraps the standard
result envelope into bare documents/lists for its callers.
"""
from app.config import settings
from app.crud.base import BaseCRUD

class ApiCRUD(BaseCRUD):
    """CRUD operations bound to the APIs collection (``settings.RESOURCES_COLLECTION``)."""

    def __init__(self):
        """Initialize API collection"""
        super().__init__(settings.RESOURCES_COLLECTION)
        
    def create(self, data: dict) -> dict:
        """Create a new API entry in the database.

        Args:
            data: The API document to insert.

        Returns:
            dict: The result envelope from :meth:`BaseCRUD.create`.
        """
        return super().create(data)

    def get(self, api_id: str) -> dict:
        """Get a single API entry by ID.

        Args:
            api_id: String form of the document's MongoDB ``_id``.

        Returns:
            dict: The bare API document (unwrapped from the result envelope),
            or ``{}`` if the envelope had no ``ResultData``.

        Raises:
            ResourceNotFoundException: If no API with that ID exists.
        """
        base_result = super().get(api_id)
        return base_result.get("ResultData", [{}])[0]  # Return just the document
        
    def search(self, **kwargs) -> list:
        """Search APIs based on parameters.

        Args:
            **kwargs: Search parameters forwarded to :meth:`BaseCRUD.search`
                (e.g. ``searchphrase``, ``skip``, ``limit``, ``include``,
                ``exclude``, ``sort.asc``/``sort.desc``).

        Returns:
            list: The matching API documents (unwrapped from the result
            envelope); empty list if none match.
        """
        base_result = super().search(**kwargs)
        return base_result.get("ResultData", [])  # Return just the list of documents

# Create singleton instance
api_crud = ApiCRUD()