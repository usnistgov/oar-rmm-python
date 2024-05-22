from pydantic import BaseModel
from typing import Dict, List, Any

class SearchResult(BaseModel):
    Metrics: Dict[str, Any]
    ResultCount: int
    PageSize: int
    ResultData: List[Any]
    