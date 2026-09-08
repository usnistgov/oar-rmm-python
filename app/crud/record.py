"""CRUD operations for the "records" resource collection (the core dataset metadata).

Records are the primary resource of the RMM API — dataset/publication metadata
documents served at ``/records``. Beyond the basic ID lookup and pagination
inherited from :class:`~app.crud.base.BaseCRUD`, this module implements
:meth:`RecordCRUD.search`, which runs a single MongoDB ``$facet`` aggregation
pipeline to return a paginated page of matching records *and* facet counts
(topics, resource types, components, authors, keywords) in one round-trip,
including optional counts contributed by the external "code"/"papers"/"patents"
collections when the caller has selected those product types.

See also ``app.crud.facets`` for the standalone full-corpus (non-paginated)
facet aggregation endpoint.
"""
from __future__ import annotations

import time
from app.crud.base import BaseCRUD
from app.config import settings
from app.database import db
import logging
import re
from app.middleware.request_processor import ProcessRequest
from app.middleware.exceptions import (
    InternalServerException,
    ResourceNotFoundException,
    KeyWordNotFoundException,
    IllegalArgumentException,
)

logger = logging.getLogger(__name__)


def _is_type_condition(condition: dict) -> bool:
    """Return True if a query condition is solely about the @type field."""
    if not condition or not isinstance(condition, dict):
        return False
    # Direct single-key: {"@type": ...}
    if "@type" in condition and len(condition) == 1:
        return True
    # OR of @type conditions: {"$or": [{"@type": ...}, ...]}
    if "$or" in condition and len(condition) == 1:
        return all(
            isinstance(c, dict) and "@type" in c and len(c) == 1
            for c in condition["$or"]
        )
    return False


def _strip_type_filter(query: dict) -> dict:
    """
    Return a copy of query with all @type conditions removed.
    Used for exclude-self faceting on resourceTypes so that selecting a type
    does not collapse the other buckets.
    """
    if not query or not isinstance(query, dict):
        return query or {}

    # $and: filter out any clause that is purely an @type condition
    if "$and" in query:
        kept = [
            _strip_type_filter(c)
            for c in query["$and"]
            if not _is_type_condition(c)
        ]
        kept = [c for c in kept if c]  # drop empty dicts produced by recursion
        if not kept:
            return {}
        if len(kept) == 1:
            return kept[0]
        return {"$and": kept}

    # Top-level direct @type condition
    if "@type" in query and len(query) == 1:
        return {}

    return query


# ---------------------------------------------------------------------------
# External product-type facet support
# ---------------------------------------------------------------------------
# The non-data corpora (code repositories, papers, patents) live in their own
# collections, each with a wildcard ($**) text index but none of the
# record-specific fields (topic.tag, @type, components.@type, ...). Their
# resourceTypes counts must therefore be scoped to the free-text intent of the
# request rather than pulled as static global corpus totals.
#
# product-key -> (collection name, resourceTypes label)
_EXTERNAL_PRODUCTS = [
    ("code",    "code",    "Code Repository"),
    ("papers",  "papers",  "Paper"),
    ("patents", "patents", "Patent"),
]

# Friendly synonyms the UI may send for each product key.
_PRODUCT_ALIASES = {
    "data": "data", "dataset": "data", "datasets": "data",
    "record": "data", "records": "data",
    "code": "code", "coderepository": "code", "coderepo": "code",
    "paper": "papers", "papers": "papers",
    "patent": "patents", "patents": "patents",
}

_EXTERNAL_KEYS = {"code", "papers", "patents"}
_FALSY_FLAGS = {"", "0", "false", "no", "off", "none", "null"}


def _parse_product_selection(products, external) -> set:
    """
    Return the subset of external product keys ({"code", "papers", "patents"})
    whose counts belong in the resourceTypes facet.

    Parameters
    ----------
    products : optional comma-separated selection among data/code/papers/patents.
               None / absent => all products selected (backward compatible).
    external : optional master switch; when falsy ("false"/"0"/...), all external
               product counts are suppressed regardless of `products`.

    Deselecting a product type (omitting it from `products`) removes its bucket,
    so its resourceTypes entry drops to the count within the current result set.

    Args:
        products: Raw ``products`` query-parameter value (comma-separated
            string of product keys/aliases), or ``None``.
        external: Raw ``external`` query-parameter value acting as a master
            on/off switch for external product counts, or ``None``.

    Returns:
        set: Subset of ``{"code", "papers", "patents"}`` to include.
    """
    if external is not None and str(external).strip().lower() in _FALSY_FLAGS:
        return set()

    if not products:
        return set(_EXTERNAL_KEYS)

    selected = set()
    for token in str(products).split(","):
        key = _PRODUCT_ALIASES.get(token.strip().lower().replace(" ", ""))
        if key in _EXTERNAL_KEYS:
            selected.add(key)
    return selected


def _external_text_query(searchphrase, topic_tag) -> dict:
    """
    Build a $text query that scopes the external product collections to the same
    free-text intent as the records query (searchphrase + selected topic label).

    The external collections have wildcard text indexes but no topic.tag/@type
    fields, so the searchphrase and topic label(s) are folded into a single
    $text search — the same text-search mechanism their own /papers, /code and
    /patents endpoints use. Returns {} when there is no searchphrase and no
    topic (an unfiltered browse), for which the full-corpus total is correct.

    Args:
        searchphrase: Free-text search term from the records query, or empty.
        topic_tag: Comma-separated ``topic.tag`` filter value(s) from the
            records query, or empty.

    Returns:
        dict: A MongoDB ``$text`` query dict, or ``{}`` if there are no terms.
    """
    terms = []
    if searchphrase:
        term = str(searchphrase).strip()
        if term:
            terms.append(term)
    for tag in str(topic_tag or "").split(","):
        tag = tag.strip()
        if tag:
            terms.append(tag)
    if not terms:
        return {}
    return {"$text": {"$search": " ".join(terms)}}


class RecordCRUD(BaseCRUD):
    """CRUD operations bound to the records collection (``settings.RECORDS_COLLECTION``)."""

    def __init__(self):
        super().__init__(settings.RECORDS_COLLECTION)

    def get(self, record_id: str) -> dict:
        """Get a single record by @id, EDIID, or ARK identifier.

        URL-decodes ``record_id`` and tries several matching strategies in a
        single query: exact match on ``ediid`` or ``@id``, then (if the ID
        does not already start with ``"ark:"``) a match with an ``"ark:"``
        prefix prepended, and finally a suffix regex match against ``ediid``
        and ``@id`` to tolerate partial/MDS-style identifiers.

        Args:
            record_id: A record identifier — full ARK ID, EDIID, ``@id``, or
                MDS-style suffix. May be URL-encoded (e.g. ``ark%3A...``).

        Returns:
            dict: ``{"ResultCount": 1, "ResultData": [doc], "Metrics": {...}}``.

        Raises:
            ResourceNotFoundException: If no record matches any strategy.
            InternalServerException: If the query fails for any other reason.
        """
        start_time = time.time()
        print('Getting record with ID:', record_id)
        try:
            # URL decode the record_id (convert %3A back to :)
            from urllib.parse import unquote
            decoded_id = unquote(record_id)
            
            # Build query conditions similar to metrics lookup
            query_conditions = [
                {"ediid": decoded_id},
                {"@id": decoded_id}
            ]
            
            # If the ID doesn't start with "ark:", try additional patterns
            if not decoded_id.startswith("ark:"):
                query_conditions.extend([
                    {"@id": f"ark:{decoded_id}"},  # Try with ark: prefix
                    {"ediid": {"$regex": f".*{re.escape(decoded_id)}$"}},  # Match at end of ediid
                    {"@id": {"$regex": f".*{re.escape(decoded_id)}$"}}     # Match at end of @id
                ])
            
            # Execute the query
            query_result = self.collection.find_one(
                {"$or": query_conditions},
                {"_id": 0}  # Use dict format for projection
            )
            
            if query_result:
                return {
                    "ResultCount": 1,
                    "ResultData": [query_result],
                    "Metrics": {"ElapsedTime": time.time() - start_time}
                }

            raise ResourceNotFoundException(f"Record with ID {decoded_id} not found")
                    
        except ResourceNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving record: {e}")
            raise InternalServerException(f"Failed to retrieve record: {str(e)}")
        
    def get_all(self, skip: int = 0, limit: int = 10) -> dict:
        """
        Get multiple records with pagination.
        
        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            
        Returns:
            dict: The records data with metrics
        """
        return super().get_all(skip, limit)
        
    def search(self, **kwargs) -> dict:
        """
        Search records and return paginated results plus pre-computed facet counts
        (topics, resourceTypes, components, authors, keywords) in a single MongoDB
        aggregation round-trip, eliminating the need for a separate filters request.

        Args:
            **kwargs: Raw search parameters as forwarded from the ``/records``
                router, e.g. ``searchphrase``, ``skip``, ``limit``,
                ``sort.asc``/``sort.desc``, ``include``/``exclude``, arbitrary
                field filters, plus the facet-only controls ``products``
                (comma-separated product types to include in resourceTypes)
                and ``external`` (master on/off switch for external product
                counts). ``products``/``external`` are popped before query
                construction so they never become bogus field filters.

        Returns:
            dict: ``{"ResultCount": int, "ResultData": [...], "PageSize": int,
            "Facets": {...}, "Metrics": {...}}``.

        Raises:
            KeyWordNotFoundException: If parameter processing determines no
                results are possible (propagated from ``ProcessRequest``).
            IllegalArgumentException: If the search parameters cannot be
                translated into a valid MongoDB query.
            InternalServerException: If the aggregation query fails.
        """
        start_time = time.time()
        # Product-selection controls are facet-composition inputs, not record
        # fields — pop them BEFORE building the Mongo query. Left in kwargs they
        # would become bogus conditions (e.g. {"products": {...}}) and zero out
        # ResultCount and every data facet.
        products_param = kwargs.pop("products", None)
        external_param = kwargs.pop("external", None)
        try:
            processor = ProcessRequest()
            try:
                processed = processor.process_search_params(kwargs)
                if "projection" not in processed:
                    processed["projection"] = {}
                processed["projection"]["_id"] = 0
            except Exception as e:
                logger.error(f"Error processing search parameters: {e}")
                raise IllegalArgumentException(str(e))

            query = processed["query"]
            projection = processed.get("projection", {"_id": 0})
            skip = processed.get("skip") or 0
            limit = processed.get("limit") or 0
            sort_spec = processed.get("sort") or []

            # Sub-pipeline that returns the requested page of documents
            data_pipeline: list = []
            if sort_spec:
                data_pipeline.append({"$sort": {f: d for f, d in sort_spec}})
            if skip:
                data_pipeline.append({"$skip": skip})
            if limit:
                data_pipeline.append({"$limit": limit})
            data_pipeline.append({"$project": projection})

            pipeline = [
                {"$match": query},
                {"$facet": {
                    # Paginated result set
                    "data": data_pipeline,
                    # Total matched count (unpaginated)
                    "total": [{"$count": "count"}],
                    # Research topics — level-1 only (part before first ':'),
                    # deduplicated and counts aggregated across all sub-topics.
                    "topics": [
                        {"$unwind": {"path": "$topic", "preserveNullAndEmptyArrays": False}},
                        {"$addFields": {
                            "_level1Tag": {
                                "$arrayElemAt": [{"$split": ["$topic.tag", ":"]}, 0]
                            }
                        }},
                        {"$match": {"_level1Tag": {"$ne": None, "$ne": ""}}},
                        {"$group": {"_id": "$_level1Tag", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ],
                    # Record @type values — computed separately via exclude-self
                    # aggregation below; this key is intentionally absent from $facet.
                    # Component types (components[].@type, nrdp-prefixed only)
                    "components": [
                        {"$unwind": {"path": "$components", "preserveNullAndEmptyArrays": False}},
                        {"$unwind": {"path": "$components.@type", "preserveNullAndEmptyArrays": False}},
                        {"$match": {"components.@type": {"$regex": "nrdp", "$options": "i"}}},
                        {"$group": {"_id": "$components.@type", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                    ],
                    # Authors / contributors (contactPoint.fn)
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

            # Preserve collation used by the cursor-based search for consistent sorting
            agg_kwargs: dict = {}
            if sort_spec:
                agg_kwargs["collation"] = {
                    "locale": "en",
                    "strength": 3,
                    "numericOrdering": True,
                    "caseLevel": True,
                    "alternate": "shifted",
                }

            logger.info(f"Record search query: {query}")
            result = list(self.collection.aggregate(pipeline, **agg_kwargs))

            # --- Exclude-self resourceTypes aggregation ---
            # Strip @type from the query so selecting one type doesn't collapse
            # the other buckets (same behaviour as Elasticsearch post_filter).
            query_without_type = _strip_type_filter(query)
            rt_pipeline = [
                {"$match": query_without_type} if query_without_type else {"$match": {}},
                {"$unwind": {"path": "$@type", "preserveNullAndEmptyArrays": False}},
                {"$group": {"_id": "$@type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
            ]
            rt_result = list(self.collection.aggregate(rt_pipeline))
            resource_type_buckets = [
                {"type": item["_id"], "count": item["count"]}
                for item in rt_result if item.get("_id")
            ]

            empty_facets = {
                "topics": [], "resourceTypes": [], "components": [],
                "authors": [], "keywords": [],
            }

            if not result:
                return {
                    "ResultCount": 0, "ResultData": [], "PageSize": limit,
                    "Facets": empty_facets,
                    "Metrics": {"ElapsedTime": time.time() - start_time},
                }

            bucket = result[0]
            docs = bucket.get("data", [])
            total_list = bucket.get("total", [])
            total = total_list[0]["count"] if total_list else 0

            facets = {
                "topics": [
                    {"tag": item["_id"], "count": item["count"]}
                    for item in bucket.get("topics", []) if item.get("_id")
                ],
                "resourceTypes": resource_type_buckets,
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

            # --- External product-type counts (code / papers / patents) ---
            # Scope each external corpus to the SAME free-text intent as the
            # records query (searchphrase + selected topic) instead of returning
            # static global corpus totals, and only include the product types the
            # caller actually selected. Deselecting a product type therefore drops
            # its bucket to the count within the current result set (0 / removed).
            selected_products = _parse_product_selection(products_param, external_param)
            if selected_products:
                ext_query = _external_text_query(
                    kwargs.get("searchphrase", ""),
                    kwargs.get("topic.tag", ""),
                )
                for product_key, col_name, label in _EXTERNAL_PRODUCTS:
                    if product_key not in selected_products:
                        continue
                    try:
                        count = db[col_name].count_documents(ext_query)
                        if count > 0:
                            facets["resourceTypes"].append({"type": label, "count": count})
                    except Exception as ext_err:
                        logger.warning(f"Could not count {col_name} collection: {ext_err}")

            logger.info(f"Record search returned {total} total, {len(docs)} in page")
            return {
                "ResultCount": total,
                "ResultData": docs,
                "PageSize": limit,
                "Facets": facets,
                "Metrics": {"ElapsedTime": time.time() - start_time},
            }

        except (KeyWordNotFoundException, IllegalArgumentException):
            raise
        except Exception as e:
            logger.error(f"Record search failed: {e}")
            raise InternalServerException(f"Failed to search records: {str(e)}")

# Create singleton instance
record_crud = RecordCRUD()