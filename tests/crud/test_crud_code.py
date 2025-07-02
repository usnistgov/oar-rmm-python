import unittest
from unittest.mock import patch, MagicMock
from bson import ObjectId
from app.crud.code import code_crud

class TestCodeCRUDComprehensive(unittest.TestCase):

    @patch('app.crud.base.db')
    def test_code_search_success(self, mock_db):
        """Test code CRUD search method"""
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        code_crud.collection = mock_collection
        
        with patch('app.crud.base.ProcessRequest') as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.process_search_params.return_value = {
                "query": {"language": "Python"},
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
            mock_cursor.__iter__.return_value = iter([{"name": "test_code", "language": "Python"}])
            mock_collection.find.return_value = mock_cursor
            
            result = code_crud.search(language="Python")
            
            self.assertIn("ResultData", result)

    @patch('app.crud.base.db')
    def test_code_get_all(self, mock_db):
        """Test code get_all method"""
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        code_crud.collection = mock_collection
        
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([{"name": "Test Code"}])
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 1
        
        result = code_crud.get_all()
        
        self.assertIn("ResultData", result)

    @patch('app.crud.base.db')
    def test_code_get_by_valid_id(self, mock_db):
        """Test getting code by valid ObjectId"""
        test_id = ObjectId()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        code_crud.collection = mock_collection
        
        mock_collection.find_one.return_value = {
            "_id": test_id,
            "name": "Test Code",
            "language": "Python"
        }
        
        result = code_crud.get(str(test_id))
        
        self.assertIn("ResultData", result)

if __name__ == '__main__':
    unittest.main()