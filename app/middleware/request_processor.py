from typing import Dict, Any, List, Optional
from datetime import datetime
import re
import logging
import time
from pymongo import ASCENDING, DESCENDING
from app.middleware.exceptions import (
    IllegalArgumentException, 
    ResourceNotFoundException,
    InternalServerException
)

logger = logging.getLogger(__name__)

class ProcessRequest:
    def __init__(self):
        self.reset_state()

    def reset_state(self):
        """Reset all instance variables to their default states"""
        self.filter = None
        self.projections = None
        self.sort = None
        self.page_number = 0
        self.page_size = 0
        self.page = 1
        self.logical_ops = []
        self.bson_objs = []
        self.query_list = []
        self.adv_map = {}
        self.include = ""
        self.exclude = ""
        self.filters_list = []
        self.search_phrase_filter = None
        self.filter_gte = None
        self.filter_lt = None

    def validate_input(self, params: Dict[str, Any]) -> None:
        """Validate request input parameters"""
        # Validate searchphrase
        if "searchphrase" in params and isinstance(params["searchphrase"], list):
            raise IllegalArgumentException("Only one 'searchphrase' parameter allowed per request")

        # Validate parameter sequence
        param_keys = list(params.keys())
        if "searchphrase" in param_keys and param_keys.index("searchphrase") != 0:
            raise IllegalArgumentException("searchphrase must be the first parameter")

        # Check searchphrase and logicalOp sequence
        if len(param_keys) > 1:
            if param_keys[0] == "searchphrase" and param_keys[1] == "logicalOp":
                raise IllegalArgumentException("'searchphrase' cannot be followed by 'logicalOp'")
            
        restricted_pattern = re.compile(r"[^a-z0-9.,@_]", re.IGNORECASE)
        # Check for null bytes and path traversal attempts in all parameters
        for key, value in params.items():
            if not value:
                continue
                
            # Convert value to string if it's not already
            str_value = str(value)
            
            # Check for null bytes
            if '\x00' in str_value or '%00' in str_value:
                logger.warning(f"Null byte detected in parameter {key}: {str_value}")
                raise IllegalArgumentException(f"Invalid character in parameter {key}: null bytes are not allowed")
                
            # Check for path traversal attempts
            if '../' in str_value or '..%2f' in str_value.lower():
                logger.warning(f"Path traversal attempt detected in parameter {key}: {str_value}")
                raise IllegalArgumentException(f"Invalid character sequence in parameter {key}")
                
            # Existing validation
            if key in ["exclude", "include", "sort_desc", "sort_asc"]:
                if isinstance(value, str) and restricted_pattern.search(value):
                    raise IllegalArgumentException(f"Invalid characters in {key}")
            elif key in ["skip", "limit"]:
                try:
                    int(value)
                except ValueError:
                    raise IllegalArgumentException(f"{key} must be an integer")

    def process_search_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process and build MongoDB query from request parameters"""
        self.reset_state()
        start_time = time.time()
        search_input = False

        # Define known pagination/control parameters
        control_params = {
            "searchphrase", "exclude", "include", 
            "skip", "limit", "size", "page",  
            "sort.desc", "sort.asc", 
            "datefrom", "dateto", "logicalOp"
        }
        
        try:
            self.validate_input(params)

            # First process logicalOp if present
            if "logicalOp" in params:
                self._update_map("logicalOp", params["logicalOp"])
                logger.info(f"Setting logical operator: {params['logicalOp']}")

            # Then process other parameters
            for key, value in params.items():
                if not value or key == "logicalOp":  # Skip empty values and already processed logicalOp
                    continue

                if key == "searchphrase":
                    search_input = True
                    self.search_phrase_filter = {
                        "$text": {
                            "$search": f'"{value}"' if value.startswith('"') and value.endswith('"') else value
                        }
                    }
                elif key == "exclude":
                    self.exclude = value
                elif key == "include":
                    self.include = value
                elif key == "skip":
                    self.page_number = int(value)
                elif key == "page":
                    self.page = int(value)
                    self.page_number = (self.page - 1) * (self.page_size or 10)
                elif key == "size" or key == "limit":  # Handle both size and limit
                    self.page_size = int(value)
                    if self.page > 1:  # Recalculate skip if page was set
                        self.page_number = (self.page - 1) * self.page_size
                elif key == "sort.desc":
                    self._parse_sorting([(field, DESCENDING) for field in value.split(",")])
                elif key == "sort.asc":
                    self._parse_sorting([(field, ASCENDING) for field in value.split(",")])
                elif key == "datefrom":
                    self.filter_gte = {"timestamp": {"$gte": value}}
                elif key == "dateto":
                    self.filter_lt = {"timestamp": {"$lt": value}}
                elif key not in control_params:  # Only add to adv_map if not a control parameter
                    self._update_map(key, value)

            logger.info(f"After parameter processing - Logical Ops: {self.logical_ops}")
            
            self._validate_projections()
            if self.adv_map:
                self._process_advanced_filters()

            return self._build_query(search_input, start_time)

        except IllegalArgumentException as e:
            logger.error(f"Illegal argument error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise InternalServerException(f"Error processing request: {str(e)}")

    def _parse_sorting(self, sort_items: List[tuple]) -> None:
        """Process sorting parameters"""
        try:
            self.sort = sort_items
        except Exception as e:
            logger.error(f"Error parsing sort parameters: {e}")
            raise IllegalArgumentException(f"Invalid sort parameters: {str(e)}")

    def _validate_projections(self) -> None:
        """Validate and process field projections"""
        try:
            self.projections = {}
            
            # Include fields
            if self.include:
                for field in [f.strip() for f in self.include.split(",") if f.strip()]:
                    self.projections[field] = 1

            # Exclude fields
            if self.exclude:
                for field in [f.strip() for f in self.exclude.split(",") if f.strip()]:
                    self.projections[field] = 0

            logger.info(f"Built projection: {self.projections}")
        except Exception as e:
            logger.error(f"Error building projections: {e}")
            self.projections = None

    def _update_map(self, key: str, value: str) -> None:
        """Update advanced query map with validation"""
        # Security checks
        if '\x00' in value:
            raise IllegalArgumentException(f"Invalid character in {key}: null bytes are not allowed")
        
        # Special handling for logical operators
        if key == "logicalOp":
            if value.lower() not in ["and", "or", "not"]:
                raise IllegalArgumentException(f"Invalid logical operator: {value}")
            self.logical_ops.append(value)
            return
            
        # Handle comma-separated values as OR conditions
        if ',' in value and not (value.startswith('"') and value.endswith('"')):
            # Split by comma and strip whitespace
            values = [val.strip() for val in value.split(',')]
            
            # Create a MongoDB $in query for this field
            parts = key.split('.')
            current = self.adv_map
            
            # Navigate to the nested field location
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the $in operator for the field
            current[parts[-1]] = {"$in": values}
            return
            
        # Regular non-comma values - handle dot notation
        parts = key.split('.')
        current = self.adv_map
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Just set the value directly, don't do additional append
        current[parts[-1]] = value

    def _process_advanced_filters(self) -> None:
        """Process advanced query filters"""
        search_conditions = []
        
        def process_nested_dict(prefix, nested_dict):
            """Helper to process nested dictionaries in adv_map"""
            for key, value in nested_dict.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, dict):
                    # Check if this is a MongoDB operator dict (like $in)
                    if any(k.startswith('$') for k in value.keys()):
                        search_conditions.append({full_key: value})
                    else:
                        # Recurse into nested dictionary
                        process_nested_dict(full_key, value)
                elif isinstance(value, list):
                    # Handle list values
                    for val in value:
                        if isinstance(val, str) and '\x00' in val:
                            raise IllegalArgumentException(f"Invalid character in parameter {full_key}")
                        search_conditions.append({
                            full_key: {"$regex": val, "$options": "i"}
                        })
                else:
                    # Handle single string values
                    if isinstance(value, str) and '\x00' in value:
                        raise IllegalArgumentException(f"Invalid character in parameter {full_key}")
                    
                    search_conditions.append({
                        full_key: {"$regex": value, "$options": "i"}
                    })
        
        # Process the entire adv_map
        process_nested_dict("", self.adv_map)
        
        # Rest of the function stays the same
        if not search_conditions:
            return

        logger.info(f"Processing filters - Conditions: {search_conditions}")
        logger.info(f"Processing filters - Logical Ops: {self.logical_ops}")

        if len(search_conditions) == 1:
            self.bson_objs = search_conditions
            return

        logical_op = self.logical_ops[0].lower() if self.logical_ops else "and"
        logger.info(f"Using logical operator: {logical_op}")

        if logical_op == "or":
            logger.info(f"Creating OR query with conditions: {search_conditions}")
            self.bson_objs = [{"$or": search_conditions}]
        else:
            logger.info(f"Creating AND query with conditions: {search_conditions}")
            self.bson_objs = [{"$and": search_conditions}]

    def _build_query(self, search_input: bool, start_time: float) -> Dict[str, Any]:
        """Build final MongoDB query"""
        query = {}
        
        # Add text search if present
        if self.search_phrase_filter:
            query.update(self.search_phrase_filter)

        # Add field conditions
        if self.bson_objs:
            if len(self.bson_objs) == 1:
                # Single condition or already grouped conditions
                query.update(self.bson_objs[0])
            else:
                # Multiple separate conditions
                query.update({"$and": self.bson_objs})

        # Add date filters if present
        if self.filter_gte:
            query.update(self.filter_gte)
        if self.filter_lt:
            query.update(self.filter_lt)

        logger.info(f"Final MongoDB Query: {query}")
        logger.info(f"Projections: {self.projections}")
        logger.info(f"Sort: {self.sort}")

        return {
            "query": query,
            "projection": self.projections,
            "sort": self.sort,
            "skip": self.page_number,
            "limit": self.page_size if self.page_size > 0 else 10,
            "metrics": {"elapsed_time": time.time() - start_time}
        }
    
    def _build_logical_query(self) -> Dict[str, Any]:
        """Build logical operations query"""
        if not self.bson_objs:
            return None

        query = None
        current_index = 0

        for op in self.logical_ops:
            if current_index >= len(self.bson_objs):
                break

            if op == "and":
                if query is None:
                    query = {"$and": [self.bson_objs[current_index], self.bson_objs[current_index + 1]]}
                    current_index += 2
                else:
                    query = {"$and": [query, self.bson_objs[current_index]]}
                    current_index += 1
            elif op == "or":
                if query is None:
                    query = {"$or": [self.bson_objs[current_index], self.bson_objs[current_index + 1]]}
                    current_index += 2
                else:
                    query = {"$and": [query, self.bson_objs[current_index]]}
                    current_index += 1
            elif op == "not":
                if query is None:
                    query = {"$not": self.bson_objs[current_index]}
                    current_index += 1
                else:
                    query = {"$and": [query, {"$not": self.bson_objs[current_index]}]}
                    current_index += 1

        return query