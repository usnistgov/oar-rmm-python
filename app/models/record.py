from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ContactPoint(BaseModel):
    hasEmail: Optional[str] = None
    fn: Optional[str] = None

class Inventory(BaseModel):
    forCollection: Optional[str] = None
    childCount: Optional[int] = None
    descCount: Optional[int] = None
    byType: Optional[List[Dict[str, Any]]] = None
    childCollections: Optional[List[Any]] = None

class Components(BaseModel):
    accessURL: Optional[str] = None
    type: Optional[List[str]] = Field(None, alias='@type')
    id: Optional[str] = Field(None, alias='@id')
    extensionSchemas: Optional[List[str]] = Field(None, alias='_extensionSchemas')

class Publisher(BaseModel):
    type: Optional[str] = Field(None, alias='@type')
    name: Optional[str] = None

class Record(BaseModel):
    id: Optional[str] = Field(None, alias='_id')
    context: Optional[List[Any]] = Field(None, alias='@context')
    schema_field: Optional[str] = Field(None, alias='_schema')
    extensionSchemas: Optional[List[str]] = Field(None, alias='_extensionSchemas')
    type: Optional[List[str]] = Field(None, alias='@type')
    record_id: Optional[str] = Field(None, alias='@id')
    title: Optional[str] = None
    contactPoint: Optional[ContactPoint] = None
    modified: Optional[str] = None
    status: Optional[str] = None
    ediid: Optional[str] = None
    landingPage: Optional[str] = None
    description: Optional[List[str]] = None
    keyword: Optional[List[str]] = None
    theme: Optional[List[str]] = None
    topic: Optional[List[Dict[str, str]]] = None
    references: Optional[List[Dict[str, Any]]] = None
    accessLevel: Optional[str] = None
    license: Optional[str] = None
    inventory: Optional[List[Inventory]] = None
    components: Optional[List[Components]] = None
    publisher: Optional[Publisher] = None
    language: Optional[List[str]] = None
    bureauCode: Optional[List[str]] = None
    programCode: Optional[List[str]] = None
    version: Optional[str] = None

    class Config:
        from_attributes = True