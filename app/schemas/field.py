from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class FieldValue(BaseModel):
    value: str
    label: Optional[str] = None
    description: Optional[str] = None

class Tips(BaseModel):
    search: Optional[str] = None

class FieldBase(BaseModel):
    name: str
    type: str
    item_type: Optional[str] = None
    label: Optional[str] = None
    tags: List[str] = []
    tips: Optional[Tips] = None
    values: Optional[List[FieldValue]] = None

class Field(FieldBase):
    id: Optional[str] = Field(None, alias='_id')

    class Config:
        from_attributes = True