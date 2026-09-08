"""CRUD operations for the "release sets" resource collection.

A release set groups together related versioned publications of a resource
(see also ``app.crud.version``), served at ``/releasesets``.
"""
from app.config import settings
from app.crud.base import BaseCRUD

class ReleaseSetCRUD(BaseCRUD):
    """CRUD operations bound to the release-set collection (``settings.RELEASESETS_COLLECTION``)."""

    def __init__(self):
        """Initialize release set collection"""
        super().__init__(settings.RELEASESETS_COLLECTION)
        
    def create(self, data: dict) -> dict:
        """Create a new release set entry.

        Args:
            data: The release-set document to insert.

        Returns:
            dict: The result envelope from :meth:`BaseCRUD.create`.
        """
        return super().create(data)

    def get(self, releaseset_id: str) -> dict:
        """
        Return full structured result:
        {
          "ResultCount": 1,
          "ResultData": [ { ...release set... } ],
          "Metrics": { "ElapsedTime": float }
        }
        """
        return super().get(releaseset_id)
        
    def search(self, **kwargs) -> dict:
        """
        Return full structured search result consistent with records endpoint:
        {
          "ResultCount": int,
          "ResultData": [ ... ],
          "PageSize": int,
          "Metrics": { "ElapsedTime": float }
        }
        """
        return super().search(**kwargs)

# Singleton
releaseset_crud = ReleaseSetCRUD()