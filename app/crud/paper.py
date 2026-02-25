from app.crud.base import BaseCRUD
import logging

logger = logging.getLogger(__name__)


class PaperCRUD(BaseCRUD):
    def __init__(self):
        """Initialize papers collection"""
        super().__init__("papers")

    def create(self, data: dict) -> dict:
        """Create a new paper in the database."""
        return super().create(data)

    def get(self, paper_id: str) -> dict:
        """Get a single paper by ID or alternate paper identifiers."""
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
        """Search papers with various criteria."""
        return super().search(**kwargs)


paper_crud = PaperCRUD()