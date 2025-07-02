import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app


class TestRouterRecord(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('app.crud.record.record_crud.search')
    def test_search_records_basic(self, mock_search):
        """Test basic record search"""
        mock_search.return_value = {
            "ResultData": [{"ediid": "test-1", "title": "Test Dataset"}],
            "ResultCount": 1,
            "PageSize": 10,
            "Metrics": {"ElapsedTime": 0.1}
        }
        
        response = self.client.get("/records/?searchphrase=test")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ResultData", data)
        self.assertEqual(len(data["ResultData"]), 1)

    @patch('app.crud.record.record_crud.search')
    def test_search_records_with_filters(self, mock_search):
        """Test record search with advanced filters"""
        mock_search.return_value = {
            "ResultData": [],
            "ResultCount": 0,
            "PageSize": 10,
            "Metrics": {"ElapsedTime": 0.05}
        }
        
        response = self.client.get(
            "/records/?searchphrase=test&topic.tag=Chemistry,Physics&@type=DataPublication"
        )
        
        self.assertEqual(response.status_code, 200)
        # Verify that the search was called with processed parameters
        mock_search.assert_called_once()

    @patch('app.crud.record.record_crud.get')
    def test_get_record_by_id(self, mock_get):
        """Test retrieving single record by ID"""
        mock_get.return_value = {
            "ResultData": [{"ediid": "mds2-2154", "title": "Test Dataset"}],
            "ResultCount": 1,
            "Metrics": {"ElapsedTime": 0.02}
        }
        
        response = self.client.get("/records/mds2-2154")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ResultData"][0]["ediid"], "mds2-2154")

    def test_search_records_invalid_params(self):
        """Test search with invalid parameters"""
        response = self.client.get("/records/?page=invalid_page_number")
        
        self.assertEqual(response.status_code, 400)
        
        # Test another invalid parameter
        response = self.client.get("/records/?limit=not_a_number")
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()