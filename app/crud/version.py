from app.config import settings
from app.crud.base import BaseCRUD

class VersionCRUD(BaseCRUD):
    def __init__(self):
        """Initialize versions collection"""
        super().__init__(settings.VERSIONS_COLLECTION)
        
    def create(self, data: dict) -> dict:
        """Create a new version entry in the database."""
        return super().create(data)

    def get(self, version_id: str) -> dict:
        """Get a single version entry by ID."""
        base_result = super().get(version_id)
        return base_result.get("ResultData", [{}])[0]  # Return just the document
        
    def search(self, **kwargs) -> list:
        """Search versions based on parameters."""
        base_result = super().search(**kwargs)
        return base_result.get("ResultData", [])  # Return just the list of documents

# Create singleton instance
version_crud = VersionCRUD()