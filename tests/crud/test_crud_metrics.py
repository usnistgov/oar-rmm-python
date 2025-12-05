import unittest
import math
from unittest.mock import patch, MagicMock
from app.crud.metrics import metrics_crud

class TestMetricsCRUDComprehensive(unittest.TestCase):

    def test_sanitize_float_for_json(self):
        """Test float sanitization"""
        # Test NaN
        result = metrics_crud._sanitize_float_for_json(float('nan'))
        self.assertEqual(result, 0)
        
        # Test infinity
        result = metrics_crud._sanitize_float_for_json(float('inf'))
        self.assertEqual(result, 0)
        
        # Test normal float
        result = metrics_crud._sanitize_float_for_json(3.14)
        self.assertEqual(result, 3.14)

    @patch('app.crud.metrics.metrics_crud.metrics')
    def test_get_record_metrics_success(self, mock_collection):
        """Test get record metrics success"""
        mock_collection.find_one.return_value = {
            "ediid": "test_record",
            "download_count": 100,
            "number_users": 50
        }
        
        result = metrics_crud.get_record_metrics("test_record")
        
        self.assertIsNotNone(result)
        self.assertIn("DataSetMetrics", result)
        # Check the nested structure
        data_set_metrics = result["DataSetMetrics"][0]
        self.assertIn("success_get", data_set_metrics)

    @patch('app.crud.metrics.metrics_crud.metrics')
    def test_get_record_metrics_not_found(self, mock_collection):
        """Test get record metrics when not found"""
        mock_collection.find_one.return_value = None
        
        result = metrics_crud.get_record_metrics("nonexistent")
        
        self.assertIsNone(result)

    @patch('app.crud.metrics.metrics_crud.metrics')
    def test_get_record_metrics_list_success(self, mock_collection):
        """Test get record metrics list with pagination"""
        mock_collection.find.return_value.sort.return_value.skip.return_value.limit.return_value = [
            {"ediid": "record1", "download_count": 100},
            {"ediid": "record2", "download_count": 50}
        ]
        mock_collection.count_documents.return_value = 10
        
        result = metrics_crud.get_record_metrics_list(page=1, size=2)
        
        self.assertIn("DataSetMetricsCount", result)
        self.assertIn("DataSetMetrics", result)
        self.assertEqual(result["PageSize"], 2)

    @patch('app.crud.metrics.metrics_crud.repo_metrics')
    def test_get_repo_metrics_success(self, mock_collection):
        """Test get repository metrics"""
        mock_collection.find.return_value.sort.return_value = [
            {
                "downloads": 1000,
                "unique_users": 200,
                "timestamp": "2024-01-01"
            }
        ]
        
        result = metrics_crud.get_repo_metrics()
        
        self.assertIn("RepoMetricsCount", result)
        self.assertIn("RepoMetrics", result)

    @patch('app.crud.metrics.metrics_crud.file_metrics')
    def test_get_file_metrics_by_filepath(self, mock_collection):
        """Test get file metrics by specific filepath"""
        mock_collection.find_one.return_value = {
            "filepath": "test.txt",
            "pdrid": "record123",
            "success_get": 10
        }
        
        result = metrics_crud.get_file_metrics("test.txt")
        
        self.assertIsNotNone(result)
        self.assertIn("FilesMetrics", result)

    @patch('app.crud.metrics.metrics_crud.file_metrics')
    def test_get_file_metrics_by_record_id(self, mock_collection):
        """Test get file metrics by record ID"""
        mock_collection.find.return_value = [
            {"filepath": "file1.txt", "pdrid": "record123"},
            {"filepath": "file2.txt", "pdrid": "record123"}
        ]
        
        result = metrics_crud.get_file_metrics("", recordid="record123")
        
        self.assertIsNotNone(result)
        self.assertEqual(result["FilesMetricsCount"], 2)

    @patch('app.crud.metrics.metrics_crud.metrics_base')
    def test_get_file_metrics_list_uses_metrics_base(self, mock_base):
        """Ensure file metrics list leverages MetricsBaseCRUD with defaults."""
        mock_base.process_metrics_query.return_value = {
            "FilesMetricsCount": 0,
            "PageSize": 10,
            "FilesMetrics": [],
            "Metrics": {"ElapsedTime": 0.0}
        }

        params = {"page": "2", "size": "5"}
        result = metrics_crud.get_file_metrics_list(params)

        self.assertEqual(result["PageSize"], 10)
        mock_base.process_metrics_query.assert_called_once_with(
            metrics_crud.file_metrics,
            {"page": "2", "size": "5", "sort.desc": "success_get"},
            "FilesMetrics"
        )

    @patch('app.crud.metrics.metrics_crud.metrics_base')
    def test_get_total_unique_users_uses_metrics_base(self, mock_base):
        """Ensure total users delegates to MetricsBaseCRUD with params."""
        mock_base.process_metrics_query.return_value = {
            "TotalUsersCount": 0,
            "PageSize": 10,
            "TotalUsers": [],
            "Metrics": {"ElapsedTime": 0.0}
        }

        params = {"page": "1"}
        result = metrics_crud.get_total_unique_users(params)

        self.assertEqual(result["PageSize"], 10)
        mock_base.process_metrics_query.assert_called_once_with(
            metrics_crud.unique_users,
            params,
            "TotalUsers"
        )

if __name__ == '__main__':
    unittest.main()