from app.config import settings
from app.crud.base import BaseCRUD

class VersionCRUD(BaseCRUD):
    """CRUD for versions collection returning full envelope (ResultCount, ResultData, PageSize, Metrics)."""
    def __init__(self):
        super().__init__(settings.VERSIONS_COLLECTION)

    def create(self, data: dict) -> dict:
        """Create a new version entry (returns full envelope from BaseCRUD)."""
        return super().create(data)

    def get(self, version_id: str) -> dict:
        """
        Get a single version entry by ID.

        Returns full envelope:
        {
          "ResultCount": 1 or 0,
          "ResultData": [ { ... } ] or [],
          "Metrics": { ... }
        }
        """
        return super().get(version_id)

    def search(self, **kwargs) -> dict:
        """
        Search versions with same structured response as records endpoint.

        Returns:
        {
          "ResultCount": int,
          "ResultData": [ ... ],
          "PageSize": int,
          "Metrics": { ... }
        }
        """
        return super().search(**kwargs)

# Singleton
version_crud = VersionCRUD()