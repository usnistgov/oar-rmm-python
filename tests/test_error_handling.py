import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.middleware.exceptions import ResourceNotFoundException, KeyWordNotFoundException


class TestErrorHandling(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('app.crud.record.record_crud.get')
    def test_record_not_found(self, mock_get):
        """Test 404 response when record not found"""
        mock_get.side_effect = ResourceNotFoundException("Record not found")
        
        response = self.client.get("/records/nonexistent-id")
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("message", data)

    @patch('app.crud.record.record_crud.search')
    def test_no_search_results(self, mock_search):
        """Test 404 response when no search results found"""
        mock_search.side_effect = KeyWordNotFoundException("No results found")
        
        response = self.client.get("/records/?searchphrase=nonexistent")
        
        self.assertEqual(response.status_code, 404)

    def test_invalid_parameter_validation(self):
        """Test 400 response for invalid parameters"""
        response = self.client.get("/records/?page=invalid")
        
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()