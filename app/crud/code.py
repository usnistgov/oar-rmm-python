from app.crud.base import BaseCRUD
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeCRUD(BaseCRUD):
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