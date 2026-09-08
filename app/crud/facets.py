"""
Full-corpus, multi-collection facet aggregation.

Accepts the same product selection the frontend fans out into separate search
requests (data / code / papers / patents) plus an optional searchphrase, and
returns a single merged Facets object that represents the entire selected corpus
— not just the paginated data slice.

This is the server-side equivalent of Elasticsearch's "global agg + post_filter"
pattern and eliminates the need for any client-side facet aggregation.
"""
from __future__ import annotations

import logging
from typing import Any

from app.database import db
from app.crud.record import _strip_type_filter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Collection → product-type label (used in resourceTypes facet)
# ---------------------------------------------------------------------------
_EXTERNAL_COLLECTIONS: list[tuple[str, str]] = [
    ("code",    "Code Repository"),
    ("papers",  "Paper"),
    ("patents", "Patent"),
]


def _build_text_query(searchphrase: str) -> dict:
    """Return a MongoDB $text match or {} for an optional searchphrase."""
    if not searchphrase:
        return {}
    return {"$text": {"$search": searchphrase}}


def _data_facets(searchphrase: str, extra_filters: dict | None = None) -> dict:
    """
    Run the full facet aggregation over the *records* (data) collection.

    The @type filter is excluded from the resourceTypes sub-pipeline so that
    selecting one resource type does not collapse the other buckets
    (exclude-self faceting).

    Returns a dict with keys: topics, resourceTypes, components, authors, keywords.
    """
    base_query: dict = _build_text_query(searchphrase)
    if extra_filters:
        conditions = [c for c in [base_query, extra_filters] if c]
        base_query = {"$and": conditions} if len(conditions) > 1 else (conditions[0] if conditions else {})

    query_without_type = _strip_type_filter(base_query)

    pipeline = [
        {"$match": base_query} if base_query else {"$match": {}},
        {"$facet": {
            # Level-1 research topics
            "topics": [
                {"$unwind": {"path": "$topic", "preserveNullAndEmptyArrays": False}},
                {"$addFields": {
                    "_l1": {"$arrayElemAt": [{"$split": ["$topic.tag", ":"]}, 0]}
                }},
                {"$match": {"_l1": {"$ne": None, "$gt": ""}}},
                {"$group": {"_id": "$_l1", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ],
            # Component types (nrdp-prefixed)
            "components": [
                {"$unwind": {"path": "$components", "preserveNullAndEmptyArrays": False}},
                {"$unwind": {"path": "$components.@type", "preserveNullAndEmptyArrays": False}},
                {"$match": {"components.@type": {"$regex": "nrdp", "$options": "i"}}},
                {"$group": {"_id": "$components.@type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ],
            # Authors (contactPoint.fn)
            "authors": [
                {"$match": {"contactPoint.fn": {"$exists": True, "$nin": [None, ""]}}},
                {"$group": {"_id": "$contactPoint.fn", "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}},
            ],
            # Keywords
            "keywords": [
                {"$unwind": {"path": "$keyword", "preserveNullAndEmptyArrays": False}},
                {"$group": {"_id": "$keyword", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ],
        }},
    ]

    result = list(db[_records_collection()].aggregate(pipeline))
    bucket = result[0] if result else {}

    # Exclude-self resourceTypes: run separately without @type filter
    rt_match = query_without_type if query_without_type else {}
    rt_result = list(db[_records_collection()].aggregate([
        {"$match": rt_match},
        {"$unwind": {"path": "$@type", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": "$@type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]))

    return {
        "topics": [
            {"tag": item["_id"], "count": item["count"]}
            for item in bucket.get("topics", []) if item.get("_id")
        ],
        "resourceTypes": [
            {"type": item["_id"], "count": item["count"]}
            for item in rt_result if item.get("_id")
        ],
        "components": [
            {"type": item["_id"], "count": item["count"]}
            for item in bucket.get("components", []) if item.get("_id")
        ],
        "authors": [
            {"name": item["_id"], "count": item["count"]}
            for item in bucket.get("authors", []) if item.get("_id")
        ],
        "keywords": [
            {"keyword": item["_id"], "count": item["count"]}
            for item in bucket.get("keywords", []) if item.get("_id")
        ],
    }


def _records_collection() -> str:
    """Return the configured records-collection name (imported lazily to avoid import-time coupling)."""
    from app.config import settings
    return settings.RECORDS_COLLECTION


def get_merged_facets(
    searchphrase: str = "",
    products: list[str] | None = None,
) -> dict[str, Any]:
    """
    Compute and return merged Facets for the requested product selection.

    Parameters
    ----------
    searchphrase : str
        Free-text search term forwarded to each collection.
    products : list[str] | None
        Subset of ["data", "code", "papers", "patents"]. None / empty = all.

    Returns
    -------
    dict  The Facets payload ready to embed in the API response.
    """
    if not products:
        products = ["data", "code", "papers", "patents"]

    include_data = "data" in products
    active_external = [
        (col, label)
        for col, label in _EXTERNAL_COLLECTIONS
        if label.lower().replace(" ", "") in {p.lower().replace(" ", "") for p in products}
        or col in products
    ]

    # Start with empty merged structure
    merged: dict[str, Any] = {
        "topics":        [],
        "resourceTypes": [],
        "components":    [],
        "authors":       [],
        "keywords":      [],
    }

    # --- Data facets ---
    if include_data:
        try:
            data_f = _data_facets(searchphrase)
            merged["topics"]        = data_f["topics"]
            merged["resourceTypes"] = data_f["resourceTypes"]
            merged["components"]    = data_f["components"]
            merged["authors"]       = data_f["authors"]
            merged["keywords"]      = data_f["keywords"]
        except Exception as exc:
            logger.warning("Data facet aggregation failed: %s", exc)

    # --- External collection counts (appended to resourceTypes) ---
    ext_query = _build_text_query(searchphrase)
    for col_name, label in active_external:
        try:
            count = db[col_name].count_documents(ext_query)
            if count > 0:
                merged["resourceTypes"].append({"type": label, "count": count})
        except Exception as exc:
            logger.warning("Could not count %s collection: %s", col_name, exc)

    return merged
