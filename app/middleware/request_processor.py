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
        self.logical_query = {}
        # Reset any advanced query conditions
        if hasattr(self, 'array_conditions'):
            delattr(self, 'array_conditions')
        if hasattr(self, 'field_or_conditions'):
            delattr(self, 'field_or_conditions')

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
            
            if key == "logicalOp":
                valid_logical_ops = ["AND", "OR", "and", "or"]
                if str_value not in valid_logical_ops:
                    raise IllegalArgumentException(f"Invalid logical operator: {str_value}. Must be 'AND' or 'OR'")                
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
            
            # Check if we have multiple field parameters (indicating potential logical operations)
            field_params = {k: v for k, v in params.items() 
                        if k not in control_params and v}
            
            # Handle logical operations and field grouping
            has_logical_ops = "logicalOp" in params
            has_multiple_fields = len(field_params) > 1
            logical_query = {}
            
            # Use logical processing if we have logicalOp OR multiple field parameters
            if has_logical_ops or has_multiple_fields:
                # Group fields by their logical operators
                field_groups = self._group_fields_by_logical_op(params)
                logical_query = self._build_logical_query(field_groups)
                
                # Set a flag to skip individual field processing
                use_logical_processing = True
            else:
                use_logical_processing = False
            
            # Process regular parameters
            page_specified = False
            size_specified = False
            
            for key, value in params.items():
                if not value or key == "logicalOp":
                    continue

                if key == "searchphrase":
                    search_input = True
                    self.search_phrase_filter = {
                        "$text": {
                            "$search": f'\"{value}\"' if value.startswith('"') and value.endswith('"') else value
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
                    page_specified = True
                    if size_specified:
                        self.page_number = (self.page - 1) * self.page_size
                elif key == "size" or key == "limit":
                    self.page_size = int(value)
                    size_specified = True
                    if page_specified and self.page > 1:
                        self.page_number = (self.page - 1) * self.page_size
                elif key == "sort.desc":
                    self._parse_sorting([(field, DESCENDING) for field in value.split(",")])
                elif key == "sort.asc":
                    self._parse_sorting([(field, ASCENDING) for field in value.split(",")])
                elif key == "datefrom":
                    self.filter_gte = {"timestamp": {"$gte": value}}
                elif key == "dateto":
                    self.filter_lt = {"timestamp": {"$lt": value}}
                elif key not in control_params and not use_logical_processing:
                    # Only process individual fields if not using logical operations
                    self._update_map(key, value)

            # Handle pagination defaults
            if not page_specified and not size_specified:
                self.page_size = 0
                self.page_number = 0
            elif page_specified and not size_specified:
                self.page_size = 10
                self.page_number = (self.page - 1) * self.page_size
            elif size_specified and not page_specified:
                self.page = 1
                self.page_number = 0

            # If using logical operations, set the logical query
            if logical_query:
                self.logical_query = logical_query

            self._validate_projections()
            if self.adv_map or hasattr(self, 'array_conditions') or hasattr(self, 'field_or_conditions') or hasattr(self, 'logical_query'):
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
        # Security check
        if '\x00' in value:
            raise IllegalArgumentException(f"Invalid character in {key}: null bytes are not allowed")
        
        # Handle logical operators
        if key == "logicalOp":
            if value.lower() not in ["and", "or", "not"]:
                raise IllegalArgumentException(f"Invalid logical operator: {value}")
            self.logical_ops.append(value.lower())
            return
        
        # Special handling for topic.tag
        if key == 'topic.tag':
            import re
            values = [v.strip() for v in value.split(',') if v.strip()] if ',' in value else [value.strip()]
            
            # Create case-insensitive regex patterns for topic.tag field only
            if len(values) == 1:
                condition = {"topic.tag": {"$regex": f"{re.escape(values[0])}", "$options": "i"}}
            else:
                or_conditions = []
                for val in values:
                    or_conditions.append({"topic.tag": {"$regex": f"{re.escape(val)}", "$options": "i"}})
                condition = {"$or": or_conditions}
            
            if not hasattr(self, 'field_or_conditions'):
                self.field_or_conditions = []
            
            self.field_or_conditions.append(condition)
            logger.info(f"Created topic.tag match condition: {condition}")
            return
        
        # Handle array fields with dot notation (like components.@type) 
        # @Mehdi: contactPoint is NOT an array, so handle it separately
        if '.' in key:
            base_key, sub_key = key.split('.', 1)
            
            # For array fields that contain objects (contactPoint is NOT an array)
            if base_key in ['components', 'references', 'topic', 'authors']:
                import re
                
                if ',' in value and not (value.startswith('"') and value.endswith('"')):
                    # Handle comma-separated values for OR logic
                    values = [val.strip() for val in value.split(',') if val.strip()]
                    
                    # Create individual conditions for each value
                    or_conditions = []
                    for val in values:
                        if sub_key == '@type':
                            # Use partial match for @type fields to handle prefixes
                            pattern = {"$regex": f"{re.escape(val)}", "$options": "i"}
                        else:
                            # Use partial match for other fields
                            pattern = {"$regex": f"{re.escape(val)}", "$options": "i"}
                        
                        or_conditions.append({
                            base_key: {
                                "$elemMatch": {
                                    sub_key: pattern
                                }
                            }
                        })
                    
                    # Create a single OR condition
                    condition = {"$or": or_conditions}
                else:
                    # Handle single value
                    if sub_key == '@type':
                        # Use partial match for @type to handle prefixes
                        pattern = {"$regex": f"{re.escape(value)}", "$options": "i"}
                    else:
                        pattern = {"$regex": f"{re.escape(value)}", "$options": "i"}
                    
                    condition = {
                        base_key: {
                            "$elemMatch": {
                                sub_key: pattern
                            }
                        }
                    }
                
                if not hasattr(self, 'array_conditions'):
                    self.array_conditions = []
                self.array_conditions.append(condition)
                logger.info(f"Created array condition for {base_key}.{sub_key}: {condition}")
                return
            
            # Handle contactPoint (single object, not array) and other dot notation fields
            if ',' in value and not (value.startswith('"') and value.endswith('"')):
                import re
                values = [val.strip() for val in value.split(',') if val.strip()]
                
                # For comma-separated values, create individual regex conditions
                or_conditions = []
                for val in values:
                    or_conditions.append({key: {"$regex": f"{re.escape(val)}", "$options": "i"}})
                
                # Create a single OR condition for this field
                condition = {"$or": or_conditions}
                
                if not hasattr(self, 'field_or_conditions'):
                    self.field_or_conditions = []
                self.field_or_conditions.append(condition)
                logger.info(f"Created OR field condition for {key}: {condition}")
                return
            else:
                # Handle single dot notation field (like contactPoint.fn)
                import re
                pattern = {"$regex": f"{re.escape(value)}", "$options": "i"}
                
                # Build nested dictionary structure for dot notation
                parts = key.split('.')
                current = self.adv_map
                
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                current[parts[-1]] = pattern
                return
        
        # Handle direct field queries (like @type=DataPublication)
        if ',' in value and not (value.startswith('"') and value.endswith('"')):
            import re
            values = [val.strip() for val in value.split(',') if val.strip()]
            
            # For comma-separated values, create individual regex conditions
            or_conditions = []
            for val in values:
                # Use partial match for @type fields to handle prefixes like "nrdp:DataPublication"
                if key == '@type':
                    or_conditions.append({key: {"$regex": f"{re.escape(val)}", "$options": "i"}})
                else:
                    # Use exact match for other fields
                    or_conditions.append({key: {"$regex": f"^{re.escape(val)}$", "$options": "i"}})
            
            # Create a single OR condition for this field
            condition = {"$or": or_conditions}
            
            if not hasattr(self, 'field_or_conditions'):
                self.field_or_conditions = []
            self.field_or_conditions.append(condition)
            logger.info(f"Created OR field condition for {key}: {condition}")
            return
        
        # Handle single values for direct fields
        import re
        if key == '@type':
            # Use partial match for @type to handle prefixes like "nrdp:DataPublication"
            pattern = {"$regex": f"{re.escape(value)}", "$options": "i"}
        else:
            # Use exact match for other single values
            pattern = {"$regex": f"^{re.escape(value)}$", "$options": "i"}
        
        # Build nested dictionary structure for dot notation
        parts = key.split('.')
        current = self.adv_map
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = pattern

    def _process_advanced_filters(self) -> None:
        """Process advanced query filters"""
        search_conditions = []

        # Add array conditions (these can be either AND or OR depending on the field)
        if hasattr(self, 'array_conditions'):
            search_conditions.extend(self.array_conditions)
        
        # Add field OR conditions
        if hasattr(self, 'field_or_conditions'):
            search_conditions.extend(self.field_or_conditions)
        
        # Add regular field conditions
        def process_nested_dict(prefix, nested_dict):
            for key, value in nested_dict.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, dict):
                    # Check if this is a MongoDB operator dict (like $in)
                    if any(k.startswith('$') for k in value.keys()):
                        search_conditions.append({full_key: value})
                    else:
                        # Recurse into nested dictionary
                        process_nested_dict(full_key, value)
                else:
                    # Handle single string values
                    search_conditions.append({
                        full_key: {"$regex": value, "$options": "i"}
                    })
        
        # Process the entire adv_map
        process_nested_dict("", self.adv_map)
        
        if not search_conditions:
            return

        logger.info(f"Processing filters - Conditions: {search_conditions}")
        
        self.bson_objs = search_conditions 

    def _build_query(self, search_input: bool, start_time: float) -> Dict[str, Any]:
        """Build final MongoDB query"""
        query = {}
        
        # Combine all conditions properly
        conditions = []
        
        # Add text search if present
        if self.search_phrase_filter:
            conditions.append(self.search_phrase_filter)

        # Add logical query if present
        if hasattr(self, 'logical_query') and self.logical_query:
            conditions.append(self.logical_query)

        # Add field conditions
        if self.bson_objs:
            conditions.extend(self.bson_objs)

        # Add date filters if present
        if self.filter_gte:
            conditions.append(self.filter_gte)
        if self.filter_lt:
            conditions.append(self.filter_lt)

        # Combine all conditions with $and
        if len(conditions) == 1:
            query = conditions[0]
        elif len(conditions) > 1:
            query = {"$and": conditions}

        logger.info(f"Final MongoDB Query: {query}")
        logger.info(f"Query conditions count: {len(conditions)}")
        logger.info(f"Individual conditions: {conditions}")  

        return {
            "query": query,
            "projection": self.projections,
            "sort": self.sort,
            "skip": self.page_number,
            "limit": self.page_size if self.page_size > 0 else None,  # This is correct!
            "metrics": {"elapsed_time": time.time() - start_time}
        }

    
    def _group_fields_by_logical_op(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Group fields by their associated logical operators"""
        field_groups = []
        current_group = {"fields": {}, "logicalOp": "AND"}  # Default to AND
        
        # Define control parameters to exclude from field processing
        control_params = {
            "exclude", "include", "skip", "limit", "size", "page", 
            "sort.desc", "sort.asc", "datefrom", "dateto", "searchphrase"
        }
        
        # If no logicalOp is specified, treat all fields as a single AND group
        if "logicalOp" not in params:
            for key, value in params.items():
                if key not in control_params and value:
                    current_group["fields"][key] = value
            
            if current_group["fields"]:
                field_groups.append(current_group)
            
            return field_groups
        
        # Handle explicit logicalOp parameters
        param_order = list(params.keys())
        
        # Collect all fields first
        fields_before_logical_op = {}
        fields_after_logical_op = {}
        logical_op_found = False
        logical_operator = "AND"
        
        for key in param_order:
            value = params[key]
            
            if key == "logicalOp":
                logical_op_found = True
                logical_operator = value.upper()
            elif key not in control_params and value:
                if not logical_op_found:
                    fields_before_logical_op[key] = value
                else:
                    fields_after_logical_op[key] = value
        
        # Create a single group with all fields and the specified logical operator
        all_fields = {}
        all_fields.update(fields_before_logical_op)
        all_fields.update(fields_after_logical_op)
        
        if all_fields:
            field_groups.append({
                "fields": all_fields,
                "logicalOp": logical_operator
            })
        
        return field_groups

    
    def _build_logical_query(self, field_groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build MongoDB query with proper logical operations"""
        if not field_groups:
            return {}
        
        if len(field_groups) == 1:
            # Single group - build based on its logical operator
            group = field_groups[0]
            conditions = []
            
            for field, value in group["fields"].items():
                # Handle comma-separated values for OR within same field
                if "," in str(value):
                    field_conditions = []
                    for val in str(value).split(","):
                        val = val.strip()
                        if val:
                            # Use partial match for better search results
                            field_conditions.append({field: {"$regex": f"{re.escape(val)}", "$options": "i"}})
                    if field_conditions:
                        conditions.append({"$or": field_conditions})
                else:
                    # Use partial match instead of exact match for better search results
                    conditions.append({field: {"$regex": f"{re.escape(str(value))}", "$options": "i"}})
            
            if len(conditions) == 1:
                return conditions[0]
            elif group["logicalOp"] == "OR":
                return {"$or": conditions}
            else:
                return {"$and": conditions}
        
        # Multiple groups - combine them
        group_conditions = []
        for group in field_groups:
            group_query = self._build_logical_query([group])
            if group_query:
                group_conditions.append(group_query)
        
        if len(group_conditions) == 1:
            return group_conditions[0]
        else:
            # Multiple groups are combined with AND by default
            return {"$and": group_conditions}
