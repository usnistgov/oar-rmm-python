import unittest
from unittest.mock import patch, MagicMock
from bson import ObjectId
from app.crud.field import field_crud

class TestFieldCRUD(unittest.TestCase):
    def setUp(self):
        self.crud = field_crud

    @patch('app.crud.base.db')
    def test_get_all_fields(self, mock_db):
        """Test getting all fields"""
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        self.crud.collection = mock_collection
        
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([
            {"name": "title", "type": "string"},
            {"name": "description", "type": "text"}
        ])
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 2
        
        result = self.crud.get_all(limit=10)
        
        # Based on field.py line 59, get_all returns base_result.get("ResultData", [])
        # So we expect a list, not a dict
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    @patch('app.crud.base.db')
    def test_get_all_with_pagination(self, mock_db):
        """Test get_all with pagination"""
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        self.crud.collection = mock_collection
        
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([{"name": "title"}])
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 1
        
        result = self.crud.get_all(skip=5, limit=5)
        
        self.assertIsInstance(result, list)
        mock_cursor.skip.assert_called_with(5)
        mock_cursor.limit.assert_called_with(5)

    @patch('app.crud.base.db')
    def test_field_search_success(self, mock_db):
        """Test field search method"""
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        self.crud.collection = mock_collection
        
        with patch('app.crud.base.ProcessRequest') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.process_search_params.return_value = {
                "query": {"searchable": True},
                "projection": {"_id": 0},
                "sort": None,
                "skip": 0,
                "limit": 10,
                "metrics": {"elapsed_time": 0.001}
            }
            mock_processor_class.return_value = mock_processor
            
            mock_collection.count_documents.side_effect = [1, 1]
            
            mock_cursor = MagicMock()
            mock_cursor.skip.return_value = mock_cursor
            mock_cursor.limit.return_value = mock_cursor
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.__iter__.return_value = iter([{"name": "title", "searchable": True}])
            mock_collection.find.return_value = mock_cursor
            
            result = self.crud.search(searchable=True)
            
            # Based on field.py line 103, search returns base_result.get("ResultData", [])
            # So we expect a list, not a dict
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)

    @patch('app.crud.base.db')
    def test_field_get_by_valid_id(self, mock_db):
        """Test getting field by valid ObjectId"""
        test_id = ObjectId()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        self.crud.collection = mock_collection
        
        mock_collection.find_one.return_value = {
            "_id": test_id,
            "name": "title",
            "type": "string"
        }
        
        result = self.crud.get(str(test_id))
        
        self.assertIn("ResultData", result)
        self.assertEqual(result["ResultCount"], 1)

    @patch('app.crud.base.db')
    def test_field_get_not_found(self, mock_db):
        """Test getting field that doesn't exist"""
        test_id = ObjectId()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        self.crud.collection = mock_collection
        
        mock_collection.find_one.return_value = None
        
        from app.middleware.exceptions import ResourceNotFoundException
        with self.assertRaises(ResourceNotFoundException):
            self.crud.get(str(test_id))

    @patch('app.crud.base.db')
    def test_field_get_all_empty_result(self, mock_db):
        """Test get_all when no fields exist"""
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        self.crud.collection = mock_collection
        
        # Mock empty result that would trigger KeyWordNotFoundException in BaseCRUD
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([])
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 0
        
        # This should raise KeyWordNotFoundException from BaseCRUD.get_all
        from app.middleware.exceptions import KeyWordNotFoundException
        with self.assertRaises(KeyWordNotFoundException):
            self.crud.get_all()

    def test_field_crud_initialization(self):
        """Test that field_crud is properly initialized"""
        self.assertIsNotNone(self.crud)
        self.assertIsNotNone(self.crud.collection)

if __name__ == '__main__':
    unittest.main()