import certifi
import requests
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
import logging
import time
from fuzzywuzzy import fuzz
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

def get_latest_patent_data() -> List[Dict[str, Any]]:
    """Get patent data from the latest JSON file in outputs directory"""
    try:
        # Get the path relative to the app directory
        current_dir = Path(__file__).parent.parent
        output_directory = current_dir / "patents"
        if not output_directory.exists():
            raise HTTPException(status_code=404, detail="Patents data directory not found")
            
        files = sorted(
            output_directory.glob("*.json"), 
            key=lambda x: x.stat().st_mtime, 
            reverse=True
        )
        
        if not files:
            raise HTTPException(status_code=404, detail="No patent data files found")
            
        with open(files[0]) as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Error loading patent data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to load patent data")

def filter_fields(doc: Dict[str, Any], include: Optional[List[str]] = None, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """Filter document fields based on include/exclude lists"""
    if include:
        return {k: v for k, v in doc.items() if k in include}
    elif exclude:
        return {k: v for k, v in doc.items() if k not in exclude}
    return doc

@router.get("/patents/")
@router.get("/patents")
async def search_patents(
    searchphrase: Optional[str] = Query(None, description="Text to search for"),
    skip: int = Query(0, description="Number of patents to skip"),
    limit: int = Query(10, description="Maximum number of patents to return"),
    include: Optional[List[str]] = Query(None, description="Fields to include"),
    exclude: Optional[List[str]] = Query(None, description="Fields to exclude")
):
    """
    Search patents with fuzzy matching on Descriptive Title
    """
    start_time = time.time()
    
    try:
        # Get patent data
        patents_data = get_latest_patent_data()
        results = []
        added_titles = set()
        
        # Process each patent
        for patent in patents_data:
            title = patent.get("Descriptive Title", "")
            
            if searchphrase:
                # Perform fuzzy matching on title
                similarity_ratio = fuzz.partial_ratio(
                    title.lower(), 
                    searchphrase.lower()
                )
                
                if similarity_ratio >= 70 and title not in added_titles:
                    added_titles.add(title)
                    filtered_patent = filter_fields(patent, include, exclude)
                    results.append(filtered_patent)
            else:
                # If no search phrase, include all patents (subject to field filtering)
                if title not in added_titles:
                    added_titles.add(title)
                    filtered_patent = filter_fields(patent, include, exclude)
                    results.append(filtered_patent)
        
        # Apply pagination
        paginated_results = results[skip:skip + limit]
        
        return {
            "ResultData": paginated_results,
            "ResultCount": len(results),
            "PageSize": limit,
            "Metrics": {"ElapsedTime": time.time() - start_time}
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Patent search error: {str(e)}")
        return {
            "error": str(e),
            "ResultCount": 0,
            "ResultData": [],
            "Metrics": {"ElapsedTime": time.time() - start_time}
        }