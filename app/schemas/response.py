from pydantic import BaseModel
from typing import List, Any

class SearchResult(BaseModel):
    ResultCount: int
    PageSize: int
    ResultData: List[Any]