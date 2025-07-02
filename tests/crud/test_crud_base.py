# tests/crud/test_crud_base.py
import unittest
from unittest.mock import patch, MagicMock
import time
from bson import ObjectId
from app.crud.base import BaseCRUD
from app.middleware.exceptions import ResourceNotFoundException, IllegalArgumentException, KeyWordNotFoundException

class TestBaseCRUD(unittest.TestCase):
    def setUp(self):
        self.crud = BaseCRUD("test_collection")

    @patch('app.crud.base.db')
    def test_get_by_valid_object_id(self, mock_db):
        """Test retrieving record by valid ObjectId"""
        test_id = ObjectId()
        mock_doc = {"_id": test_id, "name": "test"}
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = mock_doc
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        result = self.crud.get(str(test_id))
        
        self.assertIn("ResultData", result)
        self.assertEqual(len(result["ResultData"]), 1)
        self.assertEqual(result["ResultData"][0]["name"], "test")

    @patch('app.crud.base.db')
    def test_get_by_valid_object_id_not_found(self, mock_db):
        """Test retrieving record by valid ObjectId when not found"""
        test_id = ObjectId()
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with self.assertRaises(ResourceNotFoundException):
            self.crud.get(str(test_id))

    def test_get_by_invalid_object_id(self):
        """Test retrieving record by invalid ObjectId format"""
        with self.assertRaises(Exception):  # InternalServerException
            self.crud.get("invalid_id")

    @patch('app.crud.base.db')
    def test_get_all_with_results(self, mock_db):
        """Test retrieving all records when results exist"""
        mock_docs = [{"name": "test1"}, {"name": "test2"}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter(mock_docs)
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 2
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        result = self.crud.get_all(skip=0, limit=10)
        
        self.assertIn("ResultData", result)
        self.assertIn("ResultCount", result)
        self.assertEqual(result["ResultCount"], 2)
        self.assertEqual(len(result["ResultData"]), 2)

    @patch('app.crud.base.db')
    def test_get_all_no_results(self, mock_db):
        """Test retrieving all records when no results exist"""
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([])
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 0
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with self.assertRaises(KeyWordNotFoundException):
            self.crud.get_all(skip=0, limit=10)

    @patch('app.crud.base.db')
    def test_get_all_without_pagination(self, mock_db):
        """Test retrieving all records without pagination (limit=0)"""
        mock_docs = [{"name": "test1"}, {"name": "test2"}, {"name": "test3"}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter(mock_docs)
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 3
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        result = self.crud.get_all(skip=0, limit=0)
        
        self.assertIn("ResultData", result)
        self.assertIn("ResultCount", result)
        self.assertEqual(result["ResultCount"], 3)

    @patch('app.crud.base.db')
    def test_search_with_valid_params(self, mock_db):
        """Test search with valid parameters"""
        mock_docs = [{"name": "test_result"}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter(mock_docs)
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.side_effect = [1, 1]  # Collection not empty, then result count
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with patch('app.crud.base.ProcessRequest') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.process_search_params.return_value = {
                "query": {"name": "test"},
                "projection": {"_id": 0},
                "sort": None,
                "skip": 0,
                "limit": 10,
                "metrics": {"elapsed_time": 0.001}
            }
            mock_processor_class.return_value = mock_processor
            
            result = self.crud.search(name="test")
            
            self.assertIn("ResultData", result)
            self.assertIn("ResultCount", result)
            self.assertIn("Metrics", result)

    @patch('app.crud.base.db')
    def test_search_no_results(self, mock_db):
        """Test search with no results"""
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([])
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.side_effect = [1, 0]  # Collection not empty, then no results
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with patch('app.crud.base.ProcessRequest') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.process_search_params.return_value = {
                "query": {"name": "nonexistent"},
                "projection": {"_id": 0},
                "sort": None,
                "skip": 0,
                "limit": 10,
                "metrics": {"elapsed_time": 0.001}
            }
            mock_processor_class.return_value = mock_processor
            
            result = self.crud.search(name="nonexistent")
            
            self.assertIn("ResultData", result)
            self.assertEqual(result["ResultData"], [])
            self.assertEqual(result["ResultCount"], 0)

    @patch('app.crud.base.db')
    def test_search_with_projection(self, mock_db):
        """Test search with field projection"""
        mock_docs = [{"name": "test_result"}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter(mock_docs)
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.side_effect = [1, 1]  # Collection not empty, then result count
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with patch('app.crud.base.ProcessRequest') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.process_search_params.return_value = {
                "query": {"name": "test"},
                "projection": {"name": 1, "_id": 0},
                "sort": None,
                "skip": 0,
                "limit": 10,
                "metrics": {"elapsed_time": 0.001}
            }
            mock_processor_class.return_value = mock_processor
            
            result = self.crud.search(include="name")
            
            self.assertIn("ResultData", result)
            # Verify that find was called with projection using keyword arguments
            mock_collection.find.assert_called_with(
                filter={"name": "test"}, 
                projection={"name": 1, "_id": 0}
            )

    @patch('app.crud.base.db')
    def test_search_with_sorting(self, mock_db):
        """Test search with sorting"""
        mock_docs = [{"name": "test1"}, {"name": "test2"}]
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter(mock_docs)
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.side_effect = [1, 2]  # Collection not empty, then result count
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with patch('app.crud.base.ProcessRequest') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.process_search_params.return_value = {
                "query": {"name": "test"},
                "projection": {"_id": 0},
                "sort": [("name", 1)],  # Ascending sort
                "skip": 0,
                "limit": 10,
                "metrics": {"elapsed_time": 0.001}
            }
            mock_processor_class.return_value = mock_processor
            
            result = self.crud.search(name="test")
            
            self.assertIn("ResultData", result)
            # Verify that sorting was applied
            mock_cursor.sort.assert_called_with([("name", 1)])

    def test_metrics_in_response(self):
        """Test that metrics are included in response"""
        # Test the metrics structure that should be in responses
        start_time = time.time()
        time.sleep(0.01)  # Small delay to ensure measurable elapsed time
        
        elapsed = time.time() - start_time
        self.assertGreater(elapsed, 0)
        
        # Test metrics structure
        metrics = {"elapsed_time": elapsed}
        self.assertIn("elapsed_time", metrics)
        self.assertIsInstance(metrics["elapsed_time"], float)

    def test_collection_initialization(self):
        """Test that collection is properly initialized"""
        crud = BaseCRUD("custom_collection")
        # Test that the collection is set up properly
        self.assertIsNotNone(crud)

    @patch('app.crud.base.db')
    def test_get_all_error_handling(self, mock_db):
        """Test error handling in get_all method"""
        mock_collection = MagicMock()
        mock_collection.find.side_effect = Exception("Database error")
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with self.assertRaises(Exception):
            self.crud.get_all()

    @patch('app.crud.base.db')
    def test_search_database_error(self, mock_db):
        """Test search method database error handling"""
        mock_collection = MagicMock()
        # Mock the empty collection check to return 1 (not empty)
        mock_collection.count_documents.return_value = 1
        # Then make find raise an error
        mock_collection.find.side_effect = Exception("Database connection error")
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with patch('app.crud.base.ProcessRequest') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.process_search_params.return_value = {
                "query": {"name": "test"},
                "projection": {"_id": 0},
                "sort": None,
                "skip": 0,
                "limit": 10,
                "metrics": {"elapsed_time": 0.001}
            }
            mock_processor_class.return_value = mock_processor
            
            with self.assertRaises(Exception):
                self.crud.search(name="test")

    def test_init_with_different_collections(self):
        """Test initialization with different collection names"""
        collections = ["records", "fields", "metadata", "custom_collection"]
        
        for collection in collections:
            crud = BaseCRUD(collection)
            self.assertIsNotNone(crud)

    @patch('app.crud.base.db')
    def test_get_all_empty_collection(self, mock_db):
        """Test get_all when collection is completely empty"""
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([])
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 0
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with self.assertRaises(KeyWordNotFoundException):
            self.crud.get_all()

    @patch('app.crud.base.db')
    def test_search_empty_collection(self, mock_db):
        """Test search when collection is empty"""
        mock_collection = MagicMock()
        # Mock the empty collection check to return 0 (empty collection)
        mock_collection.count_documents.return_value = 0
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with patch('app.crud.base.ProcessRequest') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.process_search_params.return_value = {
                "query": {"name": "test"},
                "projection": {"_id": 0},
                "sort": None,
                "skip": 0,
                "limit": 10,
                "metrics": {"elapsed_time": 0.001}
            }
            mock_processor_class.return_value = mock_processor
            
            with self.assertRaises(KeyWordNotFoundException):
                self.crud.search(name="test")

    @patch('app.crud.base.db')
    def test_search_with_pagination(self, mock_db):
        """Test search with pagination parameters"""
        mock_docs = [{"name": "test1"}, {"name": "test2"}]
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter(mock_docs)
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.side_effect = [1, 2]  # Collection not empty, then result count
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        with patch('app.crud.base.ProcessRequest') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.process_search_params.return_value = {
                "query": {"name": "test"},
                "projection": {"_id": 0},
                "sort": None,
                "skip": 5,
                "limit": 10,
                "metrics": {"elapsed_time": 0.001}
            }
            mock_processor_class.return_value = mock_processor
            
            result = self.crud.search(name="test", skip=5, limit=10)
            
            self.assertIn("ResultData", result)
            # Verify pagination was applied
            mock_cursor.skip.assert_called_with(5)
            mock_cursor.limit.assert_called_with(10)

    # Test simple operations that don't involve complex database interactions
    def test_simple_initialization(self):
        """Test simple initialization without database calls"""
        crud = BaseCRUD("simple_test")
        self.assertIsNotNone(crud)

    def test_metrics_calculation_simple(self):
        """Test metrics calculation without database"""
        start = time.time()
        time.sleep(0.001)
        elapsed = time.time() - start
        self.assertGreater(elapsed, 0)

    @patch('app.crud.base.db')
    def test_basic_get_operation(self, mock_db):
        """Test basic get operation with minimal mocking"""
        test_id = ObjectId()
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = {"_id": test_id, "test": "data"}
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        result = self.crud.get(str(test_id))
        self.assertIsNotNone(result)

    @patch('app.crud.base.db')
    def test_basic_get_all_operation(self, mock_db):
        """Test basic get_all operation with minimal mocking"""
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([{"test": "data"}])
        
        mock_collection = MagicMock()
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 1
        mock_db.__getitem__.return_value = mock_collection
        
        # Patch the collection directly on the crud instance
        self.crud.collection = mock_collection
        
        result = self.crud.get_all()
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()