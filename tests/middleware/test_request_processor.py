import unittest
from unittest.mock import patch, MagicMock
from app.middleware.request_processor import ProcessRequest
from app.middleware.exceptions import IllegalArgumentException, InternalServerException


class TestProcessRequest(unittest.TestCase):
    def setUp(self):
        self.processor = ProcessRequest()

    def test_validate_input_valid_params(self):
        """Test validation with valid parameters"""
        params = {
            "searchphrase": "test",
            "page": "1",
            "size": "10",
            "include": "title,description"
        }
        # Should not raise any exceptions
        self.processor.validate_input(params)

    def test_validate_input_null_bytes(self):
        """Test validation rejects null bytes"""
        params = {"searchphrase": "test\x00malicious"}
        with self.assertRaises(IllegalArgumentException):
            self.processor.validate_input(params)

    def test_validate_input_path_traversal(self):
        """Test validation rejects path traversal attempts"""
        params = {"include": "../../../etc/passwd"}
        with self.assertRaises(IllegalArgumentException):
            self.processor.validate_input(params)

    def test_topic_tag_single_value(self):
        """Test topic.tag handling with single value"""
        self.processor._update_map("topic.tag", "Chemistry")
        self.assertTrue(hasattr(self.processor, 'field_or_conditions'))
        condition = self.processor.field_or_conditions[0]
        self.assertIn("topic.tag", condition)

    def test_topic_tag_multiple_values(self):
        """Test topic.tag handling with comma-separated values"""
        self.processor._update_map("topic.tag", "Chemistry,Physics")
        self.assertTrue(hasattr(self.processor, 'field_or_conditions'))
        condition = self.processor.field_or_conditions[0]
        self.assertIn("$or", condition)

    def test_components_type_handling(self):
        """Test components.@type field handling"""
        self.processor._update_map("components.@type", "DataFile,AccessPage")
        self.assertTrue(hasattr(self.processor, 'array_conditions'))
        condition = self.processor.array_conditions[0]
        self.assertIn("$or", condition)

    def test_direct_type_field(self):
        """Test direct @type field handling"""
        self.processor._update_map("@type", "DataPublication,Dataset")
        self.assertTrue(hasattr(self.processor, 'field_or_conditions'))
        condition = self.processor.field_or_conditions[0]
        self.assertIn("$or", condition)

    def test_contactpoint_fn_handling(self):
        """Test contactPoint.fn field handling"""
        self.processor._update_map("contactPoint.fn", "John Doe,Jane Smith")
        
        # ContactPoint.fn goes into field_or_conditions, not array_conditions
        # because contactPoint is NOT an array in your implementation
        self.assertTrue(hasattr(self.processor, 'field_or_conditions'))
        condition = self.processor.field_or_conditions[0]
        self.assertIn("$or", condition)

    def test_build_query_with_text_search(self):
        """Test query building with text search"""
        params = {
            "searchphrase": "test query",
            "topic.tag": "Chemistry",
            "page": "1",
            "size": "10"
        }
        result = self.processor.process_search_params(params)
        
        self.assertIn("query", result)
        query = result["query"]
        self.assertIn("$and", query)
        self.assertTrue(any("$text" in condition for condition in query["$and"]))

    def test_pagination_handling(self):
        """Test pagination parameter processing"""
        params = {"page": "2", "size": "20"}
        result = self.processor.process_search_params(params)
        
        self.assertEqual(result["skip"], 20)  # (page-1) * size
        self.assertEqual(result["limit"], 20)

    def test_projection_handling(self):
        """Test field projection handling"""
        params = {
            "include": "title,description,@type",
            "exclude": "_id"
        }
        result = self.processor.process_search_params(params)
        
        projection = result["projection"]
        self.assertEqual(projection["title"], 1)
        self.assertEqual(projection["description"], 1)
        self.assertEqual(projection["@type"], 1)
        self.assertEqual(projection["_id"], 0)


if __name__ == '__main__':
    unittest.main()