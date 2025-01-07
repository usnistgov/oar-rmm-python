from fastapi.testclient import TestClient
from app.main import app
import json
import unittest
import os

class TestFields(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        try:
            test_dir = os.path.dirname(os.path.abspath(__file__))
            fixture_path = os.path.join(test_dir, 'fixtures', 'field.json')
            with open(fixture_path) as file:
                self.test_field = json.load(file)
        except FileNotFoundError:
            self.fail(f"Test field file not found at {fixture_path}!")

    def test_get_fields(self):
        """Test retrieving all fields"""
        response = self.client.get("/fields/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("Metrics", data)
        self.assertIn("ResultCount", data)
        self.assertIn("PageSize", data)
        self.assertIn("ResultData", data)
        
        if data["ResultCount"] > 0:
            field = data["ResultData"][0]
            self.assertIn("name", field)
            self.assertIn("type", field)

    def test_get_fields_with_tags(self):
        """Test retrieving fields filtered by tags"""
        response = self.client.get("/fields/?tags=searchable")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        for field in data["ResultData"]:
            self.assertIn("searchable", field["tags"])

if __name__ == '__main__':
    unittest.main()