import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.routers.usagemetrics import sanitize_response

class TestUsageMetricsRouter(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('app.routers.usagemetrics.metrics_crud')
    def test_get_record_metrics_success(self, mock_crud):
        """Test get record metrics success"""
        mock_crud.get_record_metrics.return_value = {
            "DataSetMetricsCount": 1,
            "PageSize": 0,
            "DataSetMetrics": [{"downloads": 100, "unique_users": 50}]
        }
        
        response = self.client.get("/usagemetrics/records/test-record-123")
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.usagemetrics.metrics_crud')
    def test_get_record_metrics_not_found(self, mock_crud):
        """Test get record metrics when not found"""
        mock_crud.get_record_metrics.return_value = None
        
        response = self.client.get("/usagemetrics/records/nonexistent")
        self.assertEqual(response.status_code, 404)

    @patch('app.routers.usagemetrics.metrics_crud')
    def test_get_records_metrics_list(self, mock_crud):
        """Test get records metrics list with pagination"""
        mock_crud.get_record_metrics_list.return_value = {
            "DataSetMetricsCount": 10,
            "PageSize": 5,
            "DataSetMetrics": []
        }
        
        response = self.client.get("/usagemetrics/records?page=1&size=5")
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.usagemetrics.metrics_crud')
    def test_get_file_metrics_success(self, mock_crud):
        """Test get file metrics success"""
        mock_crud.get_file_metrics.return_value = {
            "FilesMetricsCount": 1,
            "FilesMetrics": [{"filepath": "test.txt", "downloads": 10}]
        }
        
        response = self.client.get("/usagemetrics/files/test.txt")
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.usagemetrics.metrics_crud')
    def test_get_file_metrics_not_found(self, mock_crud):
        """Test get file metrics when not found"""
        mock_crud.get_file_metrics.return_value = None
        
        response = self.client.get("/usagemetrics/files/nonexistent.txt")
        self.assertEqual(response.status_code, 404)

    @patch('app.routers.usagemetrics.metrics_crud')
    def test_get_files_metrics_list(self, mock_crud):
        """Test get all files metrics with sorting"""
        mock_crud.get_file_metrics_list.return_value = {
            "FilesMetricsCount": 5,
            "FilesMetrics": []
        }
        
        response = self.client.get("/usagemetrics/files?sort_by=downloads&sort_order=desc")
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.usagemetrics.metrics_crud')
    def test_get_repo_metrics(self, mock_crud):
        """Test get repository metrics"""
        mock_crud.get_repo_metrics.return_value = {
            "RepoMetricsCount": 1,
            "RepoMetrics": [{"downloads": 1000}]
        }
        
        response = self.client.get("/usagemetrics/repo")
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.usagemetrics.metrics_crud')
    def test_get_unique_users(self, mock_crud):
        """Test get unique users count"""
        mock_crud.get_total_unique_users.return_value = {
            "total_unique_users": 500
        }
        
        response = self.client.get("/usagemetrics/totalusers")
        self.assertEqual(response.status_code, 200)

    def test_sanitize_response(self):
        """Test response sanitization"""
        data = {
            "normal_value": 10,
            "nan_value": float('nan'),
            "inf_value": float('inf'),
            "nested": {
                "bad_float": float('-inf'),
                "good_value": 42
            }
        }
        
        result = sanitize_response(data)
        
        self.assertEqual(result["normal_value"], 10)
        self.assertEqual(result["nan_value"], 0)
        self.assertEqual(result["inf_value"], 0)
        self.assertEqual(result["nested"]["bad_float"], 0)
        self.assertEqual(result["nested"]["good_value"], 42)

    @patch('app.routers.usagemetrics.metrics_crud')
    def test_endpoint_accessibility(self, mock_crud):
        """Test that all endpoints are accessible and don't return method not allowed"""
        mock_crud.get_record_metrics_list.return_value = {"DataSetMetricsCount": 0, "DataSetMetrics": []}
        mock_crud.get_file_metrics_list.return_value = {"FilesMetricsCount": 0, "FilesMetrics": []}
        mock_crud.get_repo_metrics.return_value = {"RepoMetricsCount": 0, "RepoMetrics": []}
        mock_crud.get_total_unique_users.return_value = {"total_unique_users": 0}
        
        endpoints = [
            "/usagemetrics/records",
            "/usagemetrics/files", 
            "/usagemetrics/repo",
            "/usagemetrics/totalusers"
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertNotEqual(response.status_code, 405, f"Endpoint {endpoint} returned 405")

if __name__ == '__main__':
    unittest.main()