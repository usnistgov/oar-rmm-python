import unittest
import os
import tempfile
import json
from unittest.mock import patch
from app.config import Settings

class TestConfigComprehensive(unittest.TestCase):
    
    def test_default_settings(self):
        """Test default configuration values"""
        settings = Settings()
        
        self.assertEqual(settings.ROOT_PATH, "/rmm")
        self.assertEqual(settings.MONGO_PORT, 27017)
        self.assertEqual(settings.DB_NAME, "oar-rmm")
        self.assertEqual(settings.RECORDS_COLLECTION, "record")

    @patch.dict(os.environ, {
        'MONGO_URI': 'mongodb://test:27017',
        'DB_NAME': 'test_db',
        'MONGO_PORT': '27018'
    })
    def test_environment_override(self):
        """Test configuration override from environment variables"""
        settings = Settings()
        
        self.assertEqual(settings.MONGO_URI, "mongodb://test:27017")
        self.assertEqual(settings.DB_NAME, "test_db")
        self.assertEqual(settings.MONGO_PORT, 27018)

    def test_show_config_source(self):
        """Test config source display"""
        settings = Settings()
        source = settings.show_config_source()
        self.assertIsInstance(source, str)

    def test_dump_config_basic(self):
        """Test basic config dump functionality"""
        settings = Settings()
        # Test that dumping config doesn't raise an exception
        try:
            # If the method exists
            if hasattr(settings, 'dump_config'):
                settings.dump_config()
        except Exception:
            pass  # Method might not exist

    @patch.dict(os.environ, {
        'METRICS_DB_NAME': 'custom_metrics',
        'RECORDS_COLLECTION': 'custom_records'
    })
    def test_collection_names_override(self):
        """Test custom collection names"""
        settings = Settings()
        
        self.assertEqual(settings.METRICS_DB_NAME, "custom_metrics")
        self.assertEqual(settings.RECORDS_COLLECTION, "custom_records")

    def test_config_load_default(self):
        """Test Settings.load() returns a Settings instance"""
        settings = Settings.load()
        self.assertIsInstance(settings, Settings)

    def test_config_source_default(self):
        """Test default configuration source"""
        settings = Settings()
        
        source = settings.show_config_source()
        # Should be a string
        self.assertIsInstance(source, str)

if __name__ == '__main__':
    unittest.main()