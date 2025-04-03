from app.config import settings
from app.crud.base import BaseCRUD

class ApiCRUD(BaseCRUD):
    def __init__(self):
        """Initialize API collection"""
        super().__init__(settings.RESOURCES_COLLECTION)
        
    def create(self, data: dict) -> dict:
        """Create a new API entry in the database."""
        return super().create(data)

    def get(self, api_id: str) -> dict:
        """Get a single API entry by ID."""
        base_result = super().get(api_id)
        return base_result.get("ResultData", [{}])[0]  # Return just the document
        
    def search(self, **kwargs) -> list:
        """Search APIs based on parameters."""
        base_result = super().search(**kwargs)
        return base_result.get("ResultData", [])  # Return just the list of documents

# Create singleton instance
api_crud = ApiCRUD()