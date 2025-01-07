from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.crud import field as crud
from app.models.field import FieldModel
from pydantic import ValidationError

router = APIRouter()

@router.get("/fields/")
async def get_fields(tags: Optional[List[str]] = Query(None)):
    """Get all fields, optionally filtered by tags"""
    try:
        fields = crud.get_fields(tags)
        # Validate each field against the model
        validated_fields = []
        for field in fields["ResultData"]:
            try:
                validated_field = FieldModel(**field)
                validated_fields.append(validated_field.model_dump())
            except ValidationError as e:
                continue  # Skip invalid fields
                
        fields["ResultData"] = validated_fields
        fields["ResultCount"] = len(validated_fields)
        return fields
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))