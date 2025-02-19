from fastapi import APIRouter, Query
from typing import Optional, Dict, Any, List
import requests
import logging
from fuzzywuzzy import fuzz
import time

logger = logging.getLogger(__name__)

CODE_API_URL = "https://code.nist.gov/explore/code.json"

router = APIRouter()

def filter_fields(doc: Dict[str, Any], include: Optional[List[str]] = None, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """Filter document fields based on include/exclude lists"""
    if include:
        return {k: v for k, v in doc.items() if k in include}
    elif exclude:
        return {k: v for k, v in doc.items() if k not in exclude}
    return doc

@router.get("/code/")
@router.get("/code")
async def search_code(
    searchphrase: Optional[str] = Query(None, description="Text to search for"),
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(10, description="Maximum number of items to return"),
    sort_asc: Optional[List[str]] = Query(None, description="Fields to sort ascending"),
    sort_desc: Optional[List[str]] = Query(None, description="Fields to sort descending"),
    include: Optional[List[str]] = Query(None, description="Fields to include"),
    exclude: Optional[List[str]] = Query(None, description="Fields to exclude")
):
    """
    Search or list code repositories with optional fuzzy matching
    """
    start_time = time.time()
    
    try:
        response = requests.get(CODE_API_URL)
        response.raise_for_status()
        
        json_data = response.json()
        if isinstance(json_data, dict):
            json_data = [json_data]
            
        results = []
        added_repo_names = set()
        
        for item in json_data:
            releases = item.get("releases", [])
            for release in releases:
                repo_name = release.get('name')
                if not repo_name:
                    continue
                    
                if searchphrase:
                    similarity_ratio = fuzz.partial_ratio(repo_name.lower(), searchphrase.lower())
                    if similarity_ratio >= 70 and repo_name not in added_repo_names:
                        added_repo_names.add(repo_name)
                        # Filter fields before adding to results
                        filtered_release = filter_fields(release, include, exclude)
                        results.append(filtered_release)
                elif repo_name not in added_repo_names:
                    added_repo_names.add(repo_name)
                    # Filter fields before adding to results
                    filtered_release = filter_fields(release, include, exclude)
                    results.append(filtered_release)
        
        # Apply pagination
        paginated_results = results[skip:skip + limit]
        
        return {
            "ResultData": paginated_results,
            "ResultCount": len(results),
            "PageSize": limit,
            "Metrics": {"ElapsedTime": time.time() - start_time}
        }
        
    except Exception as e:
        logger.error(f"Code API error: {str(e)}")
        return {
            "error": str(e),
            "ResultCount": 0,
            "ResultData": [],
            "Metrics": {"ElapsedTime": time.time() - start_time}
        }