from fastapi import APIRouter, Query, Request
from typing import Optional
from app.crud.facets import get_merged_facets
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/facets")
@router.get("/facets/")
async def facets(
    request: Request,
    searchphrase: Optional[str] = Query(None, description="Text to search for"),
    products: Optional[str] = Query(
        None,
        description="Comma-separated product types to include: data,code,papers,patents. "
                    "Defaults to all.",
    ),
):
    """
    Return full-corpus facet counts for the selected product types.

    This endpoint computes facet aggregations over **all matching documents**
    (not page-limited) across the requested product collections and returns a
    single merged Facets object compatible with the search response schema.

    Prefered use of inferring facets from a paginated /records response when
    the user has selected multiple product types (data + code + papers + patents).

    Response shape
    --------------
    {
      "Facets": {
        "topics":        [{"tag": str, "count": int}],
        "resourceTypes": [{"type": str, "count": int}],
        "components":    [{"type": str, "count": int}],
        "authors":       [{"name": str}],
        "keywords":      [{"keyword": str}]
      }
    }
    """
    product_list = (
        [p.strip() for p in products.split(",") if p.strip()]
        if products
        else None
    )
    facet_data = get_merged_facets(
        searchphrase=searchphrase or "",
        products=product_list,
    )
    return {"Facets": facet_data}
