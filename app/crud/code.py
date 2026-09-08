"""CRUD operations for the "code" resource collection.

Catalogs NIST software/code repositories (imported from code.gov-style JSON
via ``app.scripts.populate_code``) and served at ``/code``. Uses a hard-coded
collection name (``"code"``) rather than a ``settings.*_COLLECTION`` value.
"""
from app.crud.base import BaseCRUD
import logging

logger = logging.getLogger(__name__)

class CodeCRUD(BaseCRUD):
    """CRUD operations bound to the ``code`` collection."""

    def __init__(self):
        """Initialize code collection"""
        super().__init__("code")
        
    def create(self, data: dict) -> dict:
        """
        Create a new code entry in the database.
        
        Args:
            data (dict): The code data to create
            
        Returns:
            dict: The newly created code with metrics
        """
        return super().create(data)

    def get(self, code_id: str) -> dict:
        """
        Get a single code entry by ID.
        
        Args:
            code_id (str): The ID of the code to retrieve
            
        Returns:
            dict: The code data with metrics
        """
        return super().get(code_id)

    def search(self, **kwargs) -> dict:
        """
        Search for code entries with various criteria.
        
        Args:
            **kwargs: Search parameters including:
                - searchphrase (Optional[str]): Text to search for
                - skip (int): Number of items to skip
                - limit (int): Maximum items to return
                - include (Optional[List[str]]): Fields to include
                - exclude (Optional[List[str]]): Fields to exclude
            
        Returns:
            dict: Search results with metrics
        """
        return super().search(**kwargs)

# Create singleton instance
code_crud = CodeCRUD()