import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

class TestPaperRouter(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('app.routers.paper.paper_crud')
    def test_search_papers_success(self, mock_crud):
        """Test successful paper search"""
        mock_crud.search.return_value = {
            "ResultData": [
                {"title": "Paper 1", "doi": "10.1234/test1"},
                {"title": "Paper 2", "doi": "10.1234/test2"}
            ],
            "ResultCount": 2,
            "Metrics": {"ElapsedTime": 0.15}
        }
        
        response = self.client.get("/papers/?searchphrase=chemistry")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ResultData", data)
        self.assertIn("Metrics", data)

    @patch('app.routers.paper.paper_crud')
    def test_get_paper_by_id(self, mock_crud):
        """Test get paper by ID"""
        mock_crud.get.return_value = {
            "ResultData": [{"title": "Test Paper", "doi": "10.1234/example"}],
            "Metrics": {"ElapsedTime": 0.08}
        }

        response = self.client.get("/papers/123")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ResultData", data)

    @patch('app.routers.paper.paper_crud')
    def test_search_papers_with_filters(self, mock_crud):
        """Test paper search with multiple filters"""
        mock_crud.search.return_value = {
            "ResultData": [{"title": "Filtered Paper"}],
            "ResultCount": 1,
            "Metrics": {"ElapsedTime": 0.12}
        }
        
        response = self.client.get("/papers/?searchphrase=physics&sort_desc=title")
        
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.paper.paper_crud')
    def test_search_papers_no_results(self, mock_crud):
        """Test paper search with no results"""
        from app.middleware.exceptions import KeyWordNotFoundException
        mock_crud.search.side_effect = KeyWordNotFoundException("No papers found")
        
        response = self.client.get("/papers/?searchphrase=nonexistent")
        
        self.assertEqual(response.status_code, 404)

    @patch('app.routers.paper.paper_crud')
    def test_search_papers_with_pagination(self, mock_crud):
        """Test paper search with pagination"""
        mock_crud.search.return_value = {
            "ResultData": [{"title": f"Paper {i}"} for i in range(5)],
            "ResultCount": 50,
            "Metrics": {"ElapsedTime": 0.2}
        }
        
        response = self.client.get("/papers/?skip=10&limit=5")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["ResultData"]), 5)

    @patch('app.routers.paper.paper_crud')
    def test_get_paper_with_resource_not_found(self, mock_crud):
        """Test get paper with ResourceNotFoundException"""
        from app.middleware.exceptions import ResourceNotFoundException
        mock_crud.get.side_effect = ResourceNotFoundException("Paper not found")
        
        response = self.client.get("/papers/missing")
        
        self.assertEqual(response.status_code, 404)

    @patch('app.routers.paper.paper_crud')
    def test_search_papers_empty_results(self, mock_crud):
        """Test paper search with empty results"""
        mock_crud.search.return_value = {
            "ResultData": [],
            "ResultCount": 0,
            "Metrics": {"ElapsedTime": 0.05}
        }
        
        response = self.client.get("/papers/?searchphrase=nonexistent")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ResultCount"], 0)

    @patch('app.routers.paper.paper_crud')
    def test_search_papers_with_keyword_not_found_exception(self, mock_crud):
        """Test KeyWordNotFoundException is handled by middleware"""
        from app.middleware.exceptions import KeyWordNotFoundException
        mock_crud.search.side_effect = KeyWordNotFoundException("No papers found")
        
        response = self.client.get("/papers/?searchphrase=nonexistent")
        self.assertEqual(response.status_code, 404)

    @patch('app.routers.paper.paper_crud')
    def test_paper_endpoints_exist(self, mock_crud):
        """Test that paper endpoints are accessible"""
        mock_crud.search.return_value = {
            "ResultData": [],
            "ResultCount": 0,
            "Metrics": {"ElapsedTime": 0.01}
        }
        mock_crud.get.return_value = {
            "ResultData": [{"title": "Test Paper"}],
            "Metrics": {"ElapsedTime": 0.01}
        }
        
        response = self.client.get("/papers/")
        self.assertNotEqual(response.status_code, 405)
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get("/papers/test")
        self.assertNotEqual(response.status_code, 405)
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.paper.paper_crud')
    def test_get_paper_by_identifier_success(self, mock_crud):
        """Test successful paper retrieval by paper identifier"""
        mock_crud.get.return_value = {
            "ResultData": [{"title": "Paper by Identifier", "pubID": "NIST-001"}],
            "ResultCount": 1,
            "Metrics": {"ElapsedTime": 0.1}
        }
        
        response = self.client.get("/papers/NIST-001")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ResultData", data)
        self.assertEqual(data["ResultCount"], 1)

if __name__ == '__main__':
    unittest.main()