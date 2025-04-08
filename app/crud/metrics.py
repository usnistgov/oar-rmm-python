from datetime import datetime
from app.database import db, metrics_db
from pymongo import ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)

class MetricsCRUD:
    def __init__(self):
        """Initialize metrics collections"""
        # Use the original metrics collection
        self.metrics = metrics_db.recordMetrics
        self.file_metrics = metrics_db.fileMetrics
        self.repo_metrics = metrics_db.repoMetrics
        self.unique_users = metrics_db.uniqueUsers
        
    def record_download(self, pdrid, ediid, ip_address, user_agent="", referrer="", 
                      timestamp=None, download_size=0):
        """
        Record a dataset download in the metrics collection.
        
        Args:
            pdrid (str): The PDRID of the downloaded record
            ediid (str): The EDIID of the downloaded record
            ip_address (str): The IP address of the user
            user_agent (str): The user agent string
            referrer (str): The HTTP referrer
            timestamp (datetime): The time of the download
            download_size (int): The size of the downloaded content
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        # Insert into metrics collection
        self.metrics.insert_one({
            "pdrid": pdrid,
            "ediid": ediid,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "referrer": referrer,
            "timestamp": timestamp,
            "download_size": download_size
        })
        
        # Update record metrics summary
        self._update_record_metrics(pdrid, ediid, ip_address, timestamp, download_size)
        
        # Update repository metrics
        self._update_repo_metrics(timestamp)
        
        # Update unique users
        self._update_unique_users(ip_address, timestamp)
        
    def _update_record_metrics(self, pdrid, ediid, ip_address, timestamp, download_size):
        """Update the record metrics collection with this download"""
        # Use distinct to count unique users
        unique_users = len(self.metrics.distinct("ip_address", {"ediid": ediid}))
        
        # Count total downloads
        download_count = self.metrics.count_documents({"ediid": ediid})
        
        # Find first download time
        first_record = self.metrics.find_one(
            {"ediid": ediid}, 
            sort=[("timestamp", ASCENDING)]
        )
        first_time = first_record["timestamp"] if first_record else timestamp
        
        # Update record metrics
        self.metrics.update_one(
            {"ediid": ediid},
            {
                "$set": {
                    "ediid": ediid,
                    "pdrid": pdrid,
                    "unique_users": unique_users,
                    "download_count": download_count,
                    "first_time_logged": first_time,
                    "last_time_logged": timestamp,
                    "total_download_size": download_size * download_count
                }
            },
            upsert=True
        )
    
    def _update_repo_metrics(self, timestamp):
        """Update repository metrics for the given month"""
        # Extract year and month
        year = timestamp.year
        month = timestamp.month
        
        # Count metrics for this month
        monthly_downloads = self.metrics.count_documents({
            "timestamp": {
                "$gte": datetime(year, month, 1),
                "$lt": datetime(year, month + 1 if month < 12 else 1, 1)
            }
        })
        
        monthly_unique_users = len(self.metrics.distinct("ip_address", {
            "timestamp": {
                "$gte": datetime(year, month, 1),
                "$lt": datetime(year, month + 1 if month < 12 else 1, 1)
            }
        }))
        
        # Update repo metrics
        self.repo_metrics.update_one(
            {"year": year, "month": month},
            {
                "$set": {
                    "year": year,
                    "month": month,
                    "downloads": monthly_downloads,
                    "unique_users": monthly_unique_users,
                    "last_updated": timestamp
                }
            },
            upsert=True
        )
    
    def _update_unique_users(self, ip_address, timestamp):
        """Update the unique users collection"""
        today = datetime(timestamp.year, timestamp.month, timestamp.day)
        
        # Update daily record
        self.unique_users.update_one(
            {"date": today},
            {
                "$addToSet": {"users": ip_address}
            },
            upsert=True
        )
    
    def get_record_metrics(self, record_id):
        """Get metrics for a specific record"""
        result = self.metrics.find_one({"$or": [{"pdrid": record_id}, {"ediid": record_id}]})
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
                    "total_size_download": result.get("total_download_size", 0),
                    "success_get": result.get("download_count", 0),
                    "number_users": result.get("unique_users", 0),
                    "record_download": result.get("download_count", 0)
                }
            ]
        }
    
    def get_record_metrics_list(self, page=1, size=10, sort_by="downloads", sort_order=-1):
        """Get metrics for a list of records"""
        # Determine sort field
        sort_field = "download_count" if sort_by == "total_size_download" else "number_users"
        
        # Get paginated results
        results = list(self.metrics.find(
            {},
            {"_id": 0, "pdrid": 1, "ediid": 1, "total_size_download": 1, 
            "number_users": 1, "first_time_logged": 1, "last_time_logged": 1,
            "total_download_size": 1}
        ).sort(sort_field, sort_order).skip((page - 1) * size).limit(size))
        
        # Format results
        dataset_metrics = []
        for result in results:
            dataset_metrics.append({
                "pdrid": result.get("pdrid"),
                "ediid": result.get("ediid"),
                "first_time_logged": result.get("first_time_logged"),
                "last_time_logged": result.get("last_time_logged"),
                "total_size_download": result.get("total_size_download", 0),
                "success_get": result.get("download_count", 0),
                "number_users": result.get("number_users", 0),
                "record_download": result.get("record_download", 0)
            })
        
        # Get total count for pagination
        total = self.metrics.count_documents({})
        
        return {
            "DataSetMetricsCount": total,
            "PageSize": size,
            "DataSetMetrics": dataset_metrics
        }
    
    def get_repo_metrics(self):
        """Get repository-level metrics directly from the database"""
        # Get all repository metrics sorted by date (descending)
        results = list(self.repo_metrics.find(
            {}, 
            {"_id": 0, "ip_list": 0}  # Exclude sensitive fields
        ).sort([("timestamp", DESCENDING)]))
        
        # Return in the expected format
        return {
            "RepoMetricsCount": len(results),
            "PageSize": 0,  # Since we're returning all metrics
            "RepoMetrics": results
        }
    
    def get_total_unique_users(self):
        """Get total unique users count"""
        all_users = set()
        for doc in self.unique_users.find({}, {"users": 1}):
            all_users.update(doc.get("users", []))
        
        return {"unique_users": len(all_users)}
    
    def get_file_metrics(self, file_path):
        """Get metrics for a specific file"""
        result = self.file_metrics.find_one({"filepath": file_path})
        if not result:
            return None
        
        # Format the result in the desired structure
        return {
            "FilesMetricsCount": 1,
            "PageSize": 0,
            "FilesMetrics": [
                {
                    "pdrid": result.get("pdrid"),
                    "ediid": result.get("ediid"),
                    "filepath": result.get("filepath"),
                    "downloadURL": result.get("downloadURL"),
                    "success_get": result.get("success_get", 0),
                    "failure_get": result.get("failure_get", 0),
                    "datacart_or_client": result.get("datacart_or_client", 0),
                    "total_size_download": result.get("total_size_download", 0),
                    "first_time_logged": result.get("first_time_logged"),
                    "last_time_logged": result.get("last_time_logged")
                }
            ]
        }

    def get_file_metrics_list(self, sort_by="downloads", sort_order=-1):
        """Get metrics for all files with sorting"""
        # Determine sort field
        sort_field = "success_get" if sort_by == "total_size_download" else "filepath"
        
        # Get all results with sorting
        results = list(self.file_metrics.find(
            {},
            {"_id": 0, "pdrid": 1, "ediid": 1, "filepath": 1, "downloadURL": 1, 
            "success_get": 1, "failure_get": 1, "datacart_or_client": 1,
            "total_size_download": 1, "first_time_logged": 1, "last_time_logged": 1}
        ).sort(sort_field, sort_order))
        
        # Format results
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
                "total_size_download": result.get("total_size_download", 0),
                "first_time_logged": result.get("first_time_logged"),
                "last_time_logged": result.get("last_time_logged")
            })
        
        # Get total count of files
        total = len(files_metrics)
        
        return {
            "FilesMetricsCount": total,
            "PageSize": 0,  # 0 indicates all results are returned
            "FilesMetrics": files_metrics
        }

metrics_crud = MetricsCRUD()
