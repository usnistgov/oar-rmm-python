from app.config import settings
from app.crud.base import BaseCRUD

class ReleaseSetCRUD(BaseCRUD):
    def __init__(self):
        """Initialize release set collection"""
        super().__init__(settings.RELEASESETS_COLLECTION)
        
    def create(self, data: dict) -> dict:
        """Create a new release set entry in the database."""
        return super().create(data)

    def get(self, releaseset_id: str) -> dict:
        """Get a single release set entry by ID."""
        base_result = super().get(releaseset_id)
        return base_result.get("ResultData", [{}])[0]  # Return just the document
        
    def search(self, **kwargs) -> list:
        """Search release sets based on parameters."""
        base_result = super().search(**kwargs)
        return base_result.get("ResultData", [])  # Return just the list of documents

# Create singleton instance
releaseset_crud = ReleaseSetCRUD()