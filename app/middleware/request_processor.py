from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from datetime import datetime
import re
import logging
import time
from pymongo import ASCENDING, DESCENDING

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
            raise HTTPException(
                status_code=400,
                detail="Only one 'searchphrase' parameter allowed per request"
            )

        # Validate parameter sequence
        param_keys = list(params.keys())
        if "searchphrase" in param_keys and param_keys.index("searchphrase") != 0:
            raise HTTPException(
                status_code=400,
                detail="searchphrase must be the first parameter"
            )

        # Check searchphrase and logicalOp sequence
        if len(param_keys) > 1:
            if param_keys[0] == "searchphrase" and param_keys[1] == "logicalOp":
                raise HTTPException(
                    status_code=400,
                    detail="'searchphrase' cannot be followed by 'logicalOp'"
                )

        # Validate parameter values
        restricted_pattern = re.compile(r"[^a-z0-9.,@_]", re.IGNORECASE)
        for key, value in params.items():
            if not value:
                continue

            if key in ["exclude", "include", "sort_desc", "sort_asc"]:
                if isinstance(value, str) and restricted_pattern.search(value):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid characters in {key}"
                    )
            elif key in ["skip", "limit"]:
                try:
                    int(value)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{key} must be an integer"
                    )

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

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    def _parse_sorting(self, sort_items: List[tuple]) -> None:
        """Process sorting parameters"""
        try:
            self.sort = sort_items
        except Exception as e:
            logger.error(f"Error parsing sort parameters: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid sort parameters: {e}")

    def _validate_projections(self) -> None:
        """Validate and process field projections"""
        if self.include and self.exclude:
            if self.exclude == "_id":
                self.projections = {"_id": 0}
                for field in self.include.split(","):
                    self.projections[field] = 1
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot specify both include and exclude fields"
                )
        elif self.include:
            self.projections = {field: 1 for field in self.include.split(",")}
        elif self.exclude:
            self.projections = {field: 0 for field in self.exclude.split(",")}

    def _update_map(self, key: str, value: str) -> None:
        """Update advanced query map"""
        if key == "logicalOp":
            self.logical_ops.append(value.lower())
        else:
            if key not in self.adv_map:
                self.adv_map[key] = []
            self.adv_map[key].append(value)

    def _process_advanced_filters(self) -> None:
        """Process advanced query filters"""
        search_conditions = []
        
        # Create a condition for each field-value pair
        for key, values in self.adv_map.items():
            if key != "logicalOp":
                for value in values:
                    search_conditions.append({
                        key: {
                            "$regex": value,
                            "$options": "i"
                        }
                    })
        
        if not search_conditions:
            return

        # Log the state before processing
        logger.info(f"Processing filters - Conditions: {search_conditions}")
        logger.info(f"Processing filters - Logical Ops: {self.logical_ops}")

        if len(search_conditions) == 1:
            self.bson_objs = search_conditions
            return

        # Explicitly check logical operator
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