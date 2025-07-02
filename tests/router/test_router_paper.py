import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import requests
from app.main import app
from app.routers.paper import filter_fields

class TestPaperRouter(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('app.routers.paper.requests.post')
    def test_search_papers_success(self, mock_post):
        """Test successful paper search"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"title": "Test Paper 1", "authors": ["Author 1"]},
            {"title": "Test Paper 2", "authors": ["Author 2"]}
        ]
        mock_post.return_value = mock_response
        
        response = self.client.get("/papers/?searchphrase=chemistry")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ResultData", data)
        self.assertIn("Metrics", data)

    @patch('app.routers.paper.requests.post')
    def test_search_papers_with_filters(self, mock_post):
        """Test paper search with include/exclude filters"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"title": "Filtered Paper", "abstract": "Test"}]
        mock_post.return_value = mock_response
        
        response = self.client.get("/papers/?searchphrase=physics&include=title")
        
        self.assertEqual(response.status_code, 200)

    @patch('app.routers.paper.requests.post')
    def test_search_papers_api_error(self, mock_post):
        """Test paper search when external API returns error"""
        mock_post.side_effect = requests.RequestException("API unavailable")
        
        response = self.client.get("/papers/?searchphrase=test")
        
        self.assertEqual(response.status_code, 500)

    @patch('app.routers.paper.requests.post')
    def test_search_papers_timeout(self, mock_post):
        """Test paper search timeout handling"""
        mock_post.side_effect = requests.Timeout("Request timeout")
        
        response = self.client.get("/papers/?searchphrase=test")
        
        self.assertEqual(response.status_code, 500)

    @patch('app.routers.paper.requests.post')
    def test_search_papers_http_error(self, mock_post):
        """Test paper search HTTP error handling"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        mock_post.return_value = mock_response
        
        response = self.client.get("/papers/?searchphrase=test")
        
        self.assertEqual(response.status_code, 500)

    @patch('app.routers.paper.requests.post')
    def test_search_papers_no_results(self, mock_post):
        """Test paper search with no results"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_post.return_value = mock_response
        
        response = self.client.get("/papers/?searchphrase=nonexistent")
        
        self.assertEqual(response.status_code, 404)

    def test_search_papers_invalid_parameters(self):
        """Test paper search with invalid parameters"""
        # Test both include and exclude
        response = self.client.get("/papers/?include=title&exclude=abstract")
        self.assertEqual(response.status_code, 400)
        
        # Test negative skip
        response = self.client.get("/papers/?skip=-1")
        self.assertEqual(response.status_code, 400)
        
        # Test zero limit
        response = self.client.get("/papers/?limit=0")
        self.assertEqual(response.status_code, 400)

    @patch('app.routers.paper.requests.post')
    def test_search_papers_with_pagination(self, mock_post):
        """Test paper search with pagination"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"title": f"Paper {i}"} for i in range(20)]
        mock_post.return_value = mock_response
        
        response = self.client.get("/papers/?searchphrase=test&skip=5&limit=10")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["ResultData"]), 10)

    @patch('app.routers.paper.CERT_PATH')
    @patch('app.routers.paper.requests.post')
    def test_search_papers_cert_not_found(self, mock_post, mock_cert_path):
        """Test certificate file not found"""
        mock_cert_path.exists.return_value = False
        
        response = self.client.get("/papers/?searchphrase=test")
        
        self.assertEqual(response.status_code, 500)

    def test_filter_fields_include_only(self):
        """Test filter_fields function with include only"""
        doc = {"title": "Test", "abstract": "Content", "authors": ["A1"], "id": "123"}
        result = filter_fields(doc, include=["title", "authors"])
        
        self.assertIn("title", result)
        self.assertIn("authors", result)
        self.assertNotIn("abstract", result)
        self.assertNotIn("id", result)

    def test_filter_fields_exclude_only(self):
        """Test filter_fields function with exclude only"""
        doc = {"title": "Test", "abstract": "Content", "authors": ["A1"], "id": "123"}
        result = filter_fields(doc, exclude=["abstract", "id"])
        
        self.assertIn("title", result)
        self.assertIn("authors", result)
        self.assertNotIn("abstract", result)
        self.assertNotIn("id", result)

    def test_filter_fields_no_filters(self):
        """Test filter_fields function with no filters"""
        doc = {"title": "Test", "abstract": "Content"}
        result = filter_fields(doc)
        
        self.assertEqual(result, doc)

if __name__ == '__main__':
    unittest.main()