import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

class TestPatentRouter(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('app.routers.patent.patent_crud')
    def test_search_patents_success(self, mock_crud):
        """Test successful patent search"""
        mock_crud.search.return_value = {
            "ResultData": [
                {"title": "Patent 1", "status": "Active", "laboratory": "NIST"},
                {"title": "Patent 2", "status": "Pending", "laboratory": "NIST"}
            ],
            "ResultCount": 2,
            "Metrics": {"ElapsedTime": 0.15}
        }
        
        response = self.client.get("/patents/?status=Active")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ResultData", data)
        self.assertIn("Metrics", data)

    @patch('app.routers.patent.patent_crud')
    def test_get_patent_by_id(self, mock_crud):
        """Test get patent by ID"""
        mock_crud.get.return_value = {
            "ResultData": [{"title": "Test Patent", "status": "Active"}],
            "Metrics": {"ElapsedTime": 0.08}
        }
        
        response = self.client.get("/patents/123")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ResultData", data)

    @patch('app.routers.patent.patent_crud')
    def test_search_patents_with_filters(self, mock_crud):
        """Test patent search with multiple filters"""
        mock_crud.search.return_value = {
            "ResultData": [{"title": "Filtered Patent"}],
            "ResultCount": 1,
            "Metrics": {"ElapsedTime": 0.12}
        }
        
        response = self.client.get("/patents/?laboratory=NIST&status=Active&sort_desc=title")
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.patent.patent_crud')
    def test_search_patents_no_results(self, mock_crud):
        """Test patent search with no results"""
        from app.middleware.exceptions import KeyWordNotFoundException
        mock_crud.search.side_effect = KeyWordNotFoundException("No patents found")
        
        response = self.client.get("/patents/?status=NonExistent")
        self.assertEqual(response.status_code, 404)

    @patch('app.routers.patent.patent_crud')
    def test_search_patents_with_pagination(self, mock_crud):
        """Test patent search with pagination"""
        mock_crud.search.return_value = {
            "ResultData": [{"title": f"Patent {i}"} for i in range(5)],
            "ResultCount": 50,
            "Metrics": {"ElapsedTime": 0.2}
        }
        
        response = self.client.get("/patents/?skip=10&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["ResultData"]), 5)

    @patch('app.routers.patent.patent_crud')
    def test_get_patent_with_resource_not_found(self, mock_crud):
        """Test get patent with ResourceNotFoundException"""
        from app.middleware.exceptions import ResourceNotFoundException
        mock_crud.get.side_effect = ResourceNotFoundException("Patent not found")
        
        response = self.client.get("/patents/missing")
        self.assertEqual(response.status_code, 404)

    @patch('app.routers.patent.patent_crud')
    def test_search_patents_empty_results(self, mock_crud):
        """Test patent search with empty results"""
        mock_crud.search.return_value = {
            "ResultData": [],
            "ResultCount": 0,
            "Metrics": {"ElapsedTime": 0.05}
        }
        
        response = self.client.get("/patents/?status=NonExistent")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ResultCount"], 0)

    @patch('app.routers.patent.patent_crud')
    def test_search_patents_with_keyword_not_found_exception(self, mock_crud):
        """Test KeyWordNotFoundException is handled by middleware"""
        from app.middleware.exceptions import KeyWordNotFoundException
        mock_crud.search.side_effect = KeyWordNotFoundException("No patents found")
        
        response = self.client.get("/patents/?status=NonExistent")
        self.assertEqual(response.status_code, 404)

    @patch('app.routers.patent.patent_crud')
    def test_patent_endpoints_exist(self, mock_crud):
        """Test that patent endpoints are accessible"""
        mock_crud.search.return_value = {
            "ResultData": [],
            "ResultCount": 0,
            "Metrics": {"ElapsedTime": 0.01}
        }
        mock_crud.get.return_value = {
            "ResultData": [{"title": "Test Patent"}],
            "Metrics": {"ElapsedTime": 0.01}
        }
        
        response = self.client.get("/patents/")
        self.assertNotEqual(response.status_code, 405)
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get("/patents/test")
        self.assertNotEqual(response.status_code, 405)
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.patent.patent_crud')
    def test_get_patent_by_patent_number_success(self, mock_crud):
        """Test successful patent retrieval by patent number"""
        mock_crud.get.return_value = {
            "ResultData": [{"title": "Patent by Number", "Patent #": "US123456"}],
            "ResultCount": 1,
            "Metrics": {"ElapsedTime": 0.1}
        }
        
        response = self.client.get("/patents/US123456")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ResultData", data)
        self.assertEqual(data["ResultCount"], 1)

if __name__ == '__main__':
    unittest.main()