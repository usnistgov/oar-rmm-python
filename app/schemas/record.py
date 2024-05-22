from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ContactPoint(BaseModel):
    hasEmail: Optional[str]
    fn: Optional[str]

class Inventory(BaseModel):
    forCollection: Optional[str]
    childCount: Optional[int]
    descCount: Optional[int]
    byType: Optional[List[Dict[str, Any]]]
    childCollections: Optional[List[Any]]

class Components(BaseModel):
    accessURL: Optional[str]
    type: Optional[List[str]] = Field(None, alias='@type')
    id: Optional[str] = Field(None, alias='@id')
    extensionSchemas: Optional[List[str]] = Field(None, alias='_extensionSchemas')

class Publisher(BaseModel):
    type: Optional[str] = Field(None, alias='@type')
    name: Optional[str]

class RecordBase(BaseModel):
    context: Optional[List[Any]] = Field(None, alias='@context')
    schema_field: Optional[str] = Field(None, alias='_schema')
    extensionSchemas: Optional[List[str]] = Field(None, alias='_extensionSchemas')
    type: Optional[List[str]] = Field(None, alias='@type')
    record_id: Optional[str] = Field(None, alias='@id')
    title: Optional[str]
    contactPoint: Optional[ContactPoint]
    modified: Optional[str]
    status: Optional[str]
    ediid: Optional[str]
    landingPage: Optional[str]
    description: Optional[List[str]]
    keyword: Optional[List[str]]
    theme: Optional[List[str]]
    topic: Optional[List[Dict[str, str]]]
    references: Optional[List[Dict[str, Any]]]
    accessLevel: Optional[str]
    license: Optional[str]
    inventory: Optional[List[Inventory]]
    components: Optional[List[Components]]
    publisher: Optional[Publisher]
    language: Optional[List[str]]
    bureauCode: Optional[List[str]]
    programCode: Optional[List[str]]
    version: Optional[str]
    lang: Optional[str]

class RecordCreate(RecordBase):
    pass

class Record(RecordBase):
    id: Optional[str] = Field(None, alias='_id')

    class Config:
        from_attributes = True