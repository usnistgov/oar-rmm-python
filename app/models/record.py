from pydantic import BaseModel, Field, create_model
from typing import List, Optional, Dict, Any, Type, Tuple
from copy import deepcopy
from pydantic.fields import FieldInfo


def partial_model(model: Type[BaseModel]):
    def make_field_optional(field: FieldInfo, default: Any = None) -> Tuple[Any, FieldInfo]:
        new = deepcopy(field)
        new.default = default
        new.annotation = Optional[field.annotation]  # type: ignore
        return new.annotation, new
    return create_model(
        f'Partial{model.__name__}',
        __base__=model,
        __module__=model.__module__,
        **{
            field_name: make_field_optional(field_info)
            for field_name, field_info in model.__fields__.items()
        }
    )

@partial_model
class ContactPoint(BaseModel):
    hasEmail: str
    fn: str

@partial_model
class Inventory(BaseModel):
    forCollection: str
    childCount: int
    descCount: int
    byType: List[Dict[str, Any]]
    childCollections: List[Any]

@partial_model
class Components(BaseModel):
    accessURL: str
    type: List[str] = Field(..., alias='@type')
    id: str = Field(..., alias='@id')
    extensionSchemas: List[str] = Field(..., alias='_extensionSchemas')

@partial_model
class Publisher(BaseModel):
    type: str = Field(..., alias='@type')
    name: str

@partial_model
class Record(BaseModel):
    id: Optional[str] = Field(None, alias='_id')
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

    class Config:
        from_attributes = True