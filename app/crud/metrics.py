"""CRUD operations for usage-metrics data, served under ``/usagemetrics``.

Reads from the ``metrics_db`` (a separate MongoDB database/connection from the
main resource data, see ``app.database.connect_metrics_db``) across four
collections: per-record download metrics (``recordMetrics``), per-file
download metrics (``fileMetrics``), repository-level rollups (``repoMetrics``),
and unique-user counts (``uniqueUsers``). Numeric fields are sanitized before
returning so that non-JSON-compliant floats (``NaN``/``inf``) never reach API
responses.
"""
from datetime import datetime
from app.database import db, metrics_db
from app.crud.metrics_base import MetricsBaseCRUD
from pymongo import ASCENDING, DESCENDING
import logging
import math

logger = logging.getLogger(__name__)

class MetricsCRUD:
    """Read access to the usage-metrics collections in the metrics database."""

    def __init__(self):
        """Initialize metrics collections"""
        # Use the original metrics collection
        self.metrics = metrics_db.recordMetrics
        self.file_metrics = metrics_db.fileMetrics
        self.repo_metrics = metrics_db.repoMetrics
        self.unique_users = metrics_db.uniqueUsers
        self.metrics_base = MetricsBaseCRUD()

    def _sanitize_float_for_json(self, value, default_if_non_finite=0):
        """Replace non-finite floats (``NaN``/``inf``/``-inf``) with a JSON-safe default."""
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return default_if_non_finite
        return value
    
    def get_record_metrics(self, record_id):
        """Get download/usage metrics for a single record.

        Matches ``record_id`` against ``pdrid``, ``ediid``, or ``@id``, with a
        suffix-regex fallback (matching MDS-style short identifiers) when
        ``record_id`` does not start with ``"ark:"``.

        Args:
            record_id: A PDR ID, EDIID, ``@id``, or MDS-style suffix.

        Returns:
            dict | None: ``{"DataSetMetricsCount": 1, "PageSize": 0,
            "DataSetMetrics": [metrics_dict]}``, or ``None`` if no metrics
            document matches.
        """
        query_conditions = [
            {"pdrid": record_id}, 
            {"ediid": record_id},
            {"@id": record_id}
        ]
        
        if not record_id.startswith("ark:"):
            # Try as MDS value
            query_conditions.extend([
                {"pdrid": {"$regex": f".*{record_id}$"}},  # Match MDS at end of pdrid
                {"ediid": {"$regex": f".*{record_id}$"}},  # Match MDS at end of ediid
                {"@id": {"$regex": f".*{record_id}$"}}     # Match MDS at end of @id
            ])
        
        result = self.metrics.find_one({"$or": query_conditions})
        if not result:
            return None
        
        # Format the result in the desired structure
        return {
            "DataSetMetricsCount": 1,
            "PageSize": 0,
            "DataSetMetrics": [
                {
                    "pdrid": result.get("pdrid"),
                    "ediid": result.get("ediid"),
                    "first_time_logged": result.get("first_time_logged"),
                    "last_time_logged": result.get("last_time_logged"),
                    "total_size_download": self._sanitize_float_for_json(result.get("total_size_download", 0)),
                    "success_get": self._sanitize_float_for_json(result.get("success_get", 0)),
                    "number_users": self._sanitize_float_for_json(result.get("number_users", 0)), 
                    "record_download": self._sanitize_float_for_json(result.get("record_download", 0))
                }
            ]
        }
    
    def get_record_metrics_list(self, page=1, size=10, sort_by="total_size_download", sort_order=-1):
        """Get a paginated, sorted list of per-record metrics.

        Args:
            page: 1-based page number.
            size: Number of records per page.
            sort_by: Either ``"total_size_download"`` or ``"users"``; any
                other value falls back to sorting by ``number_users``.
            sort_order: ``-1``/``"desc"`` for descending, else ascending.

        Returns:
            dict: ``{"DataSetMetricsCount": int, "PageSize": int,
            "DataSetMetrics": [metrics_dict, ...]}``.
        """
        # Determine sort field
        if sort_by == "total_size_download":
            sort_field_db = "total_size_download"
        elif sort_by == "users":
            sort_field_db = "number_users"
        else: # Default or other sort fields
            sort_field_db = "number_users" 

        mongo_sort_order = DESCENDING if sort_order == -1 or str(sort_order).lower() == "desc" else ASCENDING
        
        # Ensure projection includes all necessary fields from DB
        projection = {
            "_id": 0, "pdrid": 1, "ediid": 1, 
            "total_size_download": 1, 
            "number_users": 1,        
            "first_time_logged": 1, 
            "last_time_logged": 1,
            "record_download": 1     
        }
        
        results = list(self.metrics.find(
            {},
            projection
        ).sort(sort_field_db, mongo_sort_order).skip((page - 1) * size).limit(size))
        
        # Format results
        dataset_metrics = []
        for result in results:
            dataset_metrics.append({
                "pdrid": result.get("pdrid"),
                "ediid": result.get("ediid"),
                "first_time_logged": result.get("first_time_logged"),
                "last_time_logged": result.get("last_time_logged"),
                "total_size_download": self._sanitize_float_for_json(result.get("total_size_download", 0)),
                "success_get": self._sanitize_float_for_json(result.get("success_get", 0)),
                "number_users": self._sanitize_float_for_json(result.get("number_users", 0)),
                "record_download": self._sanitize_float_for_json(result.get("record_download", 0))
            })
        
        # Get total count for pagination
        total = self.metrics.count_documents({})
        
        return {
            "DataSetMetricsCount": total,
            "PageSize": size,
            "DataSetMetrics": dataset_metrics
        }
    
    def get_repo_metrics(self):
        """Get repository-level metrics, sorted by most recent timestamp first.

        Excludes the internal ``ip_list`` field and sanitizes non-finite
        floats (``success_download``, ``unique_users``) before returning.

        Returns:
            dict: ``{"RepoMetricsCount": int, "PageSize": 0,
            "RepoMetrics": [doc, ...]}``.
        """
        results = list(self.repo_metrics
            .find({}, {"_id": 0, "ip_list": 0})
            .sort([("timestamp", DESCENDING)])
        )

        def sanitize(v, default=0):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return default
            return v or default

        # sanitize every numeric field before returning
        for doc in results:
            doc["success_download"]     = sanitize(doc.get("success_download"))
            doc["unique_users"]  = sanitize(doc.get("unique_users"))

        return {
            "RepoMetricsCount": len(results),
            "PageSize": 0,
            "RepoMetrics": results
        }
    
    def get_file_metrics(self, file_path, recordid=None):
        """Get metrics for one file, or all files belonging to a record.

        When ``file_path`` is empty, returns every file-metrics document
        whose ``ediid``/``pdrid`` matches ``recordid`` (with an MDS-suffix
        regex fallback). When ``file_path`` is given, first tries an exact
        ``filepath`` match; if that fails and ``file_path`` doesn't look like
        a real path (no ``/`` or ``.``), it is treated as a record identifier
        instead and all of that record's files are returned.

        Args:
            file_path: Exact file path to look up, or ``""`` to look up by
                record only.
            recordid: Record identifier used when ``file_path`` is empty.

        Returns:
            dict | None: ``{"FilesMetricsCount": int, "PageSize": 0,
            "FilesMetrics": [doc, ...]}``, or ``None`` if nothing matches.
        """
        
        if not file_path:
            # Try multiple ways to find by record ID - return ALL files for this record
            query_conditions = [
                {"ediid": recordid},
                {"pdrid": recordid}
            ]
            
            # MDS-based lookups for record ID
            if not recordid.startswith("ark:"):
                query_conditions.extend([
                    {"ediid": {"$regex": f".*{recordid}$"}},
                    {"pdrid": {"$regex": f".*{recordid}$"}}
                ])
                
            results = list(self.file_metrics.find({"$or": query_conditions}))
        else:
            # First try direct filepath lookup for a single file
            result = self.file_metrics.find_one({"filepath": file_path})
            
            if result:
                results = [result]  # Convert single result to list
            else:
                # If not found and file_path doesn't look like a real filepath, 
                # treat it as a record identifier and return ALL files for that record
                if not ("/" in file_path or "." in file_path):
                    query_conditions = [
                        {"ediid": file_path},
                        {"pdrid": file_path}
                    ]
                    
                    # Add MDS-based lookups if it doesn't start with ark:
                    if not file_path.startswith("ark:"):
                        query_conditions.extend([
                            {"ediid": {"$regex": f".*{file_path}$"}},
                            {"pdrid": {"$regex": f".*{file_path}$"}}
                        ])
                        
                    results = list(self.file_metrics.find({"$or": query_conditions}))
                else:
                    results = []
        
        if not results:
            return None
        
        # Format ALL results in the desired structure
        files_metrics = []
        for result in results:
            files_metrics.append({
                "pdrid": result.get("pdrid"),
                "ediid": result.get("ediid"),
                "filepath": result.get("filepath"),
                "downloadURL": result.get("downloadURL"),
                "success_get": result.get("success_get", 0),
                "failure_get": result.get("failure_get", 0),
                "datacart_or_client": result.get("datacart_or_client", 0),
                "number_users": result.get("number_users", 0),
                "total_size_download": result.get("total_size_download", 0),
                "first_time_logged": result.get("first_time_logged"),
                "last_time_logged": result.get("last_time_logged")
            })
        
        return {
            "FilesMetricsCount": len(files_metrics),
            "PageSize": 0,
            "FilesMetrics": files_metrics
        }
    
    def get_file_metrics_list(self, params=None):
        """Get a paginated/sorted list of all file metrics.

        Args:
            params: Raw query parameters (as accepted by
                ``MetricsBaseCRUD.process_metrics_query``); if neither
                ``sort.desc`` nor ``sort.asc`` is present, defaults to sorting
                by ``success_get`` descending.

        Returns:
            dict: Result envelope keyed under ``"FilesMetrics"`` (see
            :meth:`~app.crud.metrics_base.MetricsBaseCRUD.process_metrics_query`).
        """
        params = params or {}
        params = params.copy()

        # Provide legacy defaults if no explicit sort provided
        if "sort.desc" not in params and "sort.asc" not in params:
            params["sort.desc"] = "success_get"

        return self.metrics_base.process_metrics_query(
            self.file_metrics,
            params,
            "FilesMetrics"
        )

    def get_total_unique_users(self, params=None):
        """Get a paginated list of unique-user metrics.

        Args:
            params: Raw query parameters (as accepted by
                ``MetricsBaseCRUD.process_metrics_query``).

        Returns:
            dict: Result envelope keyed under ``"TotalUsers"`` (see
            :meth:`~app.crud.metrics_base.MetricsBaseCRUD.process_metrics_query`).
        """
        params = params or {}
        return self.metrics_base.process_metrics_query(
            self.unique_users,
            params,
            "TotalUsers"
        )

metrics_crud = MetricsCRUD()

