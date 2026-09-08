"""Translates raw HTTP query parameters into MongoDB query documents.

:class:`ProcessRequest` is the central query-building engine used by nearly
every CRUD ``search`` method (via ``app.crud.base.BaseCRUD.search`` and
directly by ``app.crud.record.RecordCRUD.search``). Given the flat dict of
query-string parameters a router receives, it produces a MongoDB filter
document plus projection/sort/pagination settings, handling:

- Pagination via ``skip``/``limit`` or ``page``/``size``.
- Free-text search via ``searchphrase`` ($text search).
- Field sorting via ``sort.asc``/``sort.desc``.
- Field projection via ``include``/``exclude``.
- Date-range filtering via ``datefrom``/``dateto``.
- Per-field filters, including comma-separated OR values, dot-notation nested
  fields, and array-of-object fields (e.g. ``components.@type``) matched with
  ``$elemMatch``.
- Explicit AND/OR grouping of multiple field filters via ``logicalOp``.

Each instance is stateful and single-use: call :meth:`reset_state` (done
automatically at the start of :meth:`process_search_params`) before reusing an
instance for a new request.
"""
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
    """Stateful builder that converts raw query parameters into a MongoDB query.

    Instantiate once per request/search call; :meth:`process_search_params`
    resets internal state at the start of each call, but a fresh instance is
    still recommended per call site to avoid any cross-request state leakage.
    """

    def __init__(self):
        """Initialize a new processor with all state reset to defaults."""
        self.reset_state()

    def reset_state(self):
        """Reset all instance variables to their default (pre-query) state.

        Called both from ``__init__`` and at the start of
        :meth:`process_search_params`, so a single ``ProcessRequest`` instance
        can safely be reused across multiple queries.
        """
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
        """Validate raw request parameters before they are turned into a query.

        Enforces: at most one ``searchphrase``, that ``searchphrase`` (if
        present) is the first parameter and is not immediately followed by
        ``logicalOp``, that ``logicalOp`` is one of ``AND``/``OR`` (case
        insensitive), that ``skip``/``limit`` are integers, that
        ``exclude``/``include``/``sort_desc``/``sort_asc`` contain only
        ``[a-z0-9.,@_]`` characters, and rejects any parameter value
        containing null bytes or path-traversal sequences (``../``).

        Args:
            params: Raw request query parameters.

        Raises:
            IllegalArgumentException: If any of the above rules are violated.
        """
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
        """Build a complete MongoDB query specification from raw request parameters.

        This is the main entry point of the class. It resets state, validates
        the input (:meth:`validate_input`), determines whether field filters
        should be combined with explicit AND/OR logic (when ``logicalOp`` is
        given or more than one field filter is present) or processed
        individually, then walks every parameter to populate pagination,
        sorting, text search, date-range, and per-field filter state before
        delegating to :meth:`_build_query` to assemble the final result.

        Args:
            params: Raw request query parameters (e.g. from
                ``dict(request.query_params)``). Recognized control keys:
                ``searchphrase``, ``exclude``, ``include``, ``skip``,
                ``limit``, ``size``, ``page``, ``sort.desc``, ``sort.asc``,
                ``datefrom``, ``dateto``, ``logicalOp``. Any other key is
                treated as a field filter.

        Returns:
            Dict[str, Any]: ``{"query": dict, "projection": dict | None,
            "sort": list | None, "skip": int, "limit": int | None,
            "metrics": {"elapsed_time": float}}``.

        Raises:
            IllegalArgumentException: If ``validate_input`` rejects the
                parameters, or a value cannot be converted as expected.
            InternalServerException: If any other unexpected error occurs
                while building the query.
        """
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
                            "$search": f'\\{value}\\' if value.startswith('"') and value.endswith('"') else value
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
        """Store parsed (field, direction) sort tuples on ``self.sort``.

        Args:
            sort_items: List of ``(field_name, pymongo.ASCENDING|DESCENDING)``
                tuples, one per comma-separated field in ``sort.asc``/``sort.desc``.

        Raises:
            IllegalArgumentException: If assigning the sort items fails.
        """
        try:
            self.sort = sort_items
        except Exception as e:
            logger.error(f"Error parsing sort parameters: {e}")
            raise IllegalArgumentException(f"Invalid sort parameters: {str(e)}")

    def _validate_projections(self) -> None:
        """Build ``self.projections`` from ``self.include``/``self.exclude``.

        Converts the comma-separated ``include``/``exclude`` strings into a
        MongoDB projection dict (``{field: 1}`` for included fields,
        ``{field: 0}`` for excluded fields). On any error, falls back to
        ``self.projections = None`` (no projection) rather than raising, since
        projection is a non-critical, best-effort feature.
        """
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
        """Translate a single field=value query parameter into a MongoDB condition.

        This is the core per-field filter dispatcher, handling several cases
        in order: the reserved ``logicalOp`` key; the special-cased
        ``topic.tag`` field (case-insensitive regex, OR'd across
        comma-separated values); dot-notation array-of-object fields such as
        ``components.@type``/``references.*``/``topic.*``/``authors.*``
        (matched via ``$elemMatch``, appended to ``self.array_conditions``);
        other dot-notation fields such as ``contactPoint.fn`` (built as a
        nested dict on ``self.adv_map``, or as OR'd regex conditions on
        ``self.field_or_conditions`` when comma-separated); and finally plain
        top-level fields (OR'd regex conditions for comma-separated values,
        otherwise a single regex condition merged into ``self.adv_map``).
        ``@type`` values always use partial (substring) matching to tolerate
        namespace prefixes like ``"nrdp:DataPublication"``; other fields use
        exact (anchored) matching unless they are array/object sub-fields.

        Args:
            key: The parameter/field name, possibly dot-notated.
            value: The raw string value for that field (may be comma-separated
                for OR semantics).

        Raises:
            IllegalArgumentException: If ``value`` contains a null byte, or a
                ``logicalOp`` value that isn't ``and``/``or``/``not``.
        """
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
        """Merge all accumulated filter state into ``self.bson_objs``.

        Combines ``self.array_conditions`` (from ``$elemMatch``-based array
        field filters) and ``self.field_or_conditions`` (OR'd multi-value
        field filters) with the conditions flattened out of ``self.adv_map``
        (nested dot-notation single-value filters, converted to
        dotted-path regex conditions, or passed through as-is when already a
        MongoDB operator dict such as ``{"$in": [...]}``
        """
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
        """Assemble the final MongoDB query document and result envelope.

        Combines (in order) the free-text ``$text`` filter, the
        AND/OR-grouped ``logical_query`` (if any), the accumulated
        ``bson_objs`` field conditions, and the ``datefrom``/``dateto`` range
        filters into a single query, wrapping multiple conditions in
        ``{"$and": [...]}`` when there is more than one.

        Args:
            search_input: Whether a ``searchphrase`` was supplied (currently
                informational; not used to alter the returned structure).
            start_time: ``time.time()`` value captured at the start of
                :meth:`process_search_params`, used to compute elapsed time.

        Returns:
            Dict[str, Any]: ``{"query": dict, "projection": dict | None,
            "sort": list | None, "skip": int, "limit": int | None,
            "metrics": {"elapsed_time": float}}``.
        """
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
        """Group non-control field parameters under a single AND/OR logical operator.

        When no ``logicalOp`` is present, all field parameters are grouped
        together under the default ``"AND"`` operator. When ``logicalOp`` is
        present, all field parameters (whether they appear before or after
        ``logicalOp`` in the parameter order) are grouped under the operator
        it specifies (``.upper()``-ed).

        Args:
            params: Raw request query parameters.

        Returns:
            List[Dict[str, Any]]: A list containing at most one group dict of
            the form ``{"fields": {name: value, ...}, "logicalOp": "AND"|"OR"}``,
            or an empty list if there are no field parameters.
        """
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
        """Build a MongoDB query combining field filters with explicit AND/OR logic.

        Each field's value becomes a case-insensitive partial-match regex
        condition (comma-separated values become an ``$or`` of regex
        conditions for that field); the resulting per-field conditions within
        a group are then combined with ``$and``/``$or`` per the group's
        ``logicalOp``. Multiple groups (only produced when
        :meth:`_group_fields_by_logical_op` is extended to emit more than one)
        are combined with ``$and``.

        Args:
            field_groups: Groups as produced by :meth:`_group_fields_by_logical_op`.

        Returns:
            Dict[str, Any]: A MongoDB query dict, or ``{}`` if there are no
            field groups.
        """
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
