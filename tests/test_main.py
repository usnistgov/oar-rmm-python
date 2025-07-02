import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

class TestMainComprehensive(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_endpoint_success_with_html_file(self):
        """Test successful root endpoint with HTML file"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])

    def test_debug_record_collection_success(self):
        """Test debug record collection endpoint success"""
        response = self.client.get("/debug/record-collection")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should return some debug info
        self.assertIsInstance(data, dict)

    def test_exception_handlers_via_routes(self):
        """Test exception handlers by triggering them via routes"""
        # Test a route that doesn't exist - should trigger general exception handler
        response = self.client.get("/nonexistent-route")
        self.assertEqual(response.status_code, 404)  # FastAPI default 404

    @patch('app.main.connect_db')
    def test_startup_event_database_success(self, mock_connect_db):
        """Test startup event with successful database connection"""
        mock_db = MagicMock()
        mock_db.name = "test_db"
        mock_connect_db.return_value = mock_db
        
        from app.main import startup_event
        
        # Should not raise an exception
        try:
            startup_event()
        except Exception as e:
            self.fail(f"startup_event raised an exception: {e}")

    @patch('app.main.connect_db')
    def test_startup_event_database_failure(self, mock_connect_db):
        """Test startup event with database connection failure"""
        mock_connect_db.side_effect = Exception("Connection failed")
        
        from app.main import startup_event
        
        # Should handle DB connection failures gracefully
        try:
            startup_event()
        except Exception as e:
            self.fail(f"startup_event should handle DB failures gracefully: {e}")

if __name__ == '__main__':
    unittest.main()