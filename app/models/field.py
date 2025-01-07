from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any, Union

class FieldValue(BaseModel):
    """Represents a valid value for a field"""
    value: str
    label: Optional[str] = None
    description: Optional[str] = None

class FieldTips(BaseModel):
    """Tips for field usage"""
    search: Optional[str] = None

class FieldModel(BaseModel):
    """Represents a field in the metadata schema"""
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., description="The name of the field")
    type: str = Field(..., description="The data type of the field")
    item_type: Optional[str] = Field(None, description="For array types, the type of the array elements")
    label: Optional[str] = Field(None, description="Human-readable label for the field")
    tags: List[str] = Field(default_factory=list, description="Tags describing field properties")
    tips: Optional[FieldTips] = Field(None, description="Usage tips for the field")
    values: Optional[List[FieldValue]] = Field(None, description="Valid values for the field")

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {
            id: str
        }