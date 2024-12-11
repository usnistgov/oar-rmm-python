from fastapi.testclient import TestClient
from app.main import app
import json
import unittest
import os

class TestRecords(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        try:
            test_dir = os.path.dirname(os.path.abspath(__file__))
            fixture_path = os.path.join(test_dir, 'fixtures', 'record.json')
            with open(fixture_path) as file:
                self.test_record = json.load(file)
        except FileNotFoundError:
            self.fail(f"Test record file not found at {fixture_path}!")

    def test_search_records_empty_query(self):
        """Test searching records with empty query returns all records"""
        response = self.client.get("/records/search/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response structure
        self.assertIn("Metrics", data)
        self.assertIn("ResultCount", data)
        self.assertIn("PageSize", data)
        self.assertIn("ResultData", data)
        
        # Check default pagination
        self.assertEqual(data["PageSize"], 10)
        
    def test_search_records_with_query(self):
        """Test searching records with specific query"""
        response = self.client.get("/records/search/?query=Campus Photovoltaic")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check response structure
        self.assertIn("Metrics", data)
        self.assertIn("ResultCount", data)
        self.assertIn("PageSize", data)
        self.assertIn("ResultData", data)
        
    def test_search_records_with_pagination(self):
        """Test searching records with pagination parameters"""
        response = self.client.get("/records/search/?page=1&size=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check pagination parameters
        self.assertEqual(data["PageSize"], 5)

if __name__ == '__main__':
    unittest.main()