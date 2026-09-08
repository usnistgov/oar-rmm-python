"""CRUD operations for the "papers" resource collection.

Catalogs research papers/publications, served at ``/papers``. Uses a
hard-coded collection name (``"papers"``).
"""
from app.crud.base import BaseCRUD
import logging

logger = logging.getLogger(__name__)


class PaperCRUD(BaseCRUD):
    """CRUD operations bound to the ``papers`` collection."""

    def __init__(self):
        """Initialize papers collection"""
        super().__init__("papers")

    def create(self, data: dict) -> dict:
        """Create a new paper in the database.

        Args:
            data: The paper document to insert.

        Returns:
            dict: The result envelope from :meth:`BaseCRUD.create`.
        """
        return super().create(data)

    def get(self, paper_id: str) -> dict:
        """Get a single paper by ID or alternate paper identifiers.

        First attempts a MongoDB ``_id`` lookup via :meth:`BaseCRUD.get`. If
        that raises (e.g. ``paper_id`` is not a valid ``ObjectId``, or no
        document has that ``_id``), falls back to searching by each of
        ``pubID``, ``doi``, ``@id``, ``paper_id``, and ``id`` in turn.

        Args:
            paper_id: A MongoDB ``_id`` string, DOI, or other paper identifier.

        Returns:
            dict: ``{"ResultCount": 1, "ResultData": doc, "Metrics": {...}}``.

        Raises:
            ValueError: If no paper matches any of the attempted identifiers.
        """
        try:
            return super().get(paper_id)
        except Exception:
            for field in ["pubID", "doi", "@id", "paper_id", "id"]:
                result = self.search(**{field: paper_id})
                if result["ResultCount"] > 0:
                    return {
                        "ResultCount": 1,
                        "ResultData": result["ResultData"][0],
                        "Metrics": result["Metrics"],
                    }
            raise ValueError("Paper not found")

    def search(self, **kwargs) -> dict:
        """Search papers with various criteria.

        Args:
            **kwargs: Search parameters forwarded to :meth:`BaseCRUD.search`.

        Returns:
            dict: The result envelope from :meth:`BaseCRUD.search`.
        """
        return super().search(**kwargs)


paper_crud = PaperCRUD()