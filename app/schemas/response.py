from pydantic import BaseModel
from typing import List, Any, Dict

class Metrics(BaseModel):
    ElapsedTime: float

class SearchResult(BaseModel):
    Metrics: Metrics
    ResultCount: int
    PageSize: int
    ResultData: List[Any]