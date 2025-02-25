import certifi
import requests
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

PAPERS_API_URL = "https://tsapps-d.nist.gov/nps/nps_public_api/api/Publication/search"
PAPERS_API_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json; x-api-version=1.0"
}

router = APIRouter()

def filter_fields(doc: Dict[str, Any], include: Optional[List[str]] = None, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """Filter document fields based on include/exclude lists"""
    if include:
        return {k: v for k, v in doc.items() if k in include}
    elif exclude:
        return {k: v for k, v in doc.items() if k not in exclude}
    return doc

@router.get("/papers/")
@router.get("/papers")
async def search_papers(
    searchphrase: Optional[str] = Query(None, description="Text to search for"),
    from_date: Optional[str] = Query("2010-01-01", description="Search from date (YYYY-MM-DD)"),
    skip: int = Query(0, description="Number of papers to skip"),
    limit: int = Query(10, description="Maximum number of papers to return"),
    include: Optional[List[str]] = Query(None, description="Fields to include"),
    exclude: Optional[List[str]] = Query(None, description="Fields to exclude")
):
    """
    Search papers from the NIST Papers API.
    
    Args:
        searchphrase (str, optional): Text to search for in papers
        from_date (str, optional): Start date for search (YYYY-MM-DD)
        skip (int): Number of results to skip (pagination)
        limit (int): Maximum number of results to return
        include (List[str], optional): Fields to include in results
        exclude (List[str], optional): Fields to exclude from results
        
    Returns:
        Dict: {
            "ResultData": List of matched papers,
            "ResultCount": Total matches found,
            "PageSize": Number of results per page,
            "Metrics": Query execution metrics
        }
        
    Raises:
        HTTPException: If the Papers API request fails
    """
    start_time = time.time()
    
    try:
        verify = certifi.where()
        
        payload = {
            "searchString": searchphrase if searchphrase else "",
            "fromDate": f"{from_date}T00:00:00.000Z"
        }

        response = requests.post(
            PAPERS_API_URL,
            json=payload,
            headers=PAPERS_API_HEADERS,
            verify=verify
        )

        if response.status_code == 200:
            papers_data = response.json()
            
            # Filter fields and apply pagination
            filtered_data = [
                filter_fields(paper, include, exclude) 
                for paper in papers_data
            ][skip:skip + limit] if papers_data else []
            
            return {
                "ResultData": filtered_data,
                "ResultCount": len(papers_data),
                "PageSize": limit,
                "Metrics": {"ElapsedTime": time.time() - start_time}
            }
        else:
            logger.error(f"Papers API error: {response.status_code}")
            return {
                "error": f"Error from Papers API: {response.status_code}",
                "ResultCount": 0,
                "ResultData": [],
                "Metrics": {"ElapsedTime": time.time() - start_time}
            }

    except Exception as e:
        logger.error(f"Paper search error: {str(e)}")
        return {
            "error": str(e),
            "ResultCount": 0,
            "ResultData": [],
            "Metrics": {"ElapsedTime": time.time() - start_time}
        }