from pathlib import Path
import certifi
import requests
from fastapi import APIRouter, Depends, Request
from typing import Optional, List, Dict, Any
import logging
import time
import re
from app.middleware.exceptions import KeyWordNotFoundException, InternalServerException, IllegalArgumentException
from app.middleware.dependencies import validate_search_params

logger = logging.getLogger(__name__)

PAPERS_API_URL = "https://tsapps-d.nist.gov/nps/nps_public_api/api/Publication/search"
PAPERS_API_HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json; x-api-version=1.0"
}
CERT_PATH = Path(__file__).parent.parent / "certificates" / "nist_cert.crt"

router = APIRouter()

NERDM_CONTEXT_URL = "https://data.nist.gov/od/dm/nerdm-pub-context.jsonld"
NERDM_SCHEMA_URL = "https://data.nist.gov/od/dm/nerdm-schema/v0.7#"
NERDM_EXTENSION_SCHEMA_URL = "https://data.nist.gov/od/dm/nerdm-schema/pub/v0.7#/definitions/PublicDataResource"
NERDM_DEFAULT_TYPES = ["nrdp:PublicDataResource", "nrdp:DataPublication"]

def filter_fields(doc: Dict[str, Any], include: Optional[List[str]] = None, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """Filter document fields based on include/exclude lists"""
    if include:
        return {k: v for k, v in doc.items() if k in include}
    elif exclude:
        return {k: v for k, v in doc.items() if k not in exclude}
    return doc

def _iso_date(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    if "T" in value:
        return value.split("T", 1)[0]
    if " " in value:
        return value.split(" ", 1)[0]
    return value

def _split_keywords(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = [part.strip() for part in re.split(r"[;,|]", value) if part.strip()]
        return parts if parts else []
    return [str(value)]

def _build_doi_url(doi: Optional[str]) -> Optional[str]:
    if not doi or not isinstance(doi, str):
        return None
    doi_value = doi.strip()
    if not doi_value:
        return None
    if doi_value.lower().startswith("http://") or doi_value.lower().startswith("https://"):
        return doi_value
    if doi_value.lower().startswith("doi:"):
        doi_value = doi_value[4:].strip()
    return f"https://doi.org/{doi_value}" if doi_value else None

def _format_author_name(author: Dict[str, Any]) -> Optional[str]:
    if not isinstance(author, dict):
        return None
    parts = [
        author.get("firstName"),
        author.get("middleName"),
        author.get("lastName")
    ]
    name = " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())
    return name or None

def _select_contact_author(authors: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(authors, list):
        return None
    for author in authors:
        if isinstance(author, dict) and author.get("primaryContact") in (1, True, "1", "true", "True"):
            return author
    return authors[0] if authors else None

def _build_paper_id(paper: Dict[str, Any], doi_url: Optional[str], landing_page: Optional[str]) -> Optional[str]:
    if doi_url:
        return doi_url
    if landing_page:
        return landing_page
    report_num = paper.get("pubReportNum")
    if isinstance(report_num, str) and report_num.strip():
        return report_num.strip()
    pub_id = paper.get("pubID")
    if pub_id is not None:
        return f"paper:{pub_id}"
    return None

def _prune_empty_fields(record: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in record.items() if v not in (None, [], {}, "")}

def map_paper_to_nerdm(paper: Dict[str, Any]) -> Dict[str, Any]:
    doi_url = _build_doi_url(paper.get("doi"))
    landing_page = paper.get("web_link") or doi_url
    paper_id = _build_paper_id(paper, doi_url, landing_page)
    pub_id = paper.get("pubID")
    contact_author = _select_contact_author(paper.get("authors"))
    contact_name = _format_author_name(contact_author) if contact_author else None
    keywords = _split_keywords(paper.get("keywords"))
    theme = [paper.get("research_Field")] if paper.get("research_Field") else []
    description = []
    if isinstance(paper.get("abstract"), str) and paper.get("abstract").strip():
        description = [paper.get("abstract").strip()]

    record = {
        "_id": str(pub_id) if pub_id is not None else paper_id,
        "@context": [NERDM_CONTEXT_URL, {"@base": paper_id}] if paper_id else [NERDM_CONTEXT_URL],
        "_schema": NERDM_SCHEMA_URL,
        "_extensionSchemas": [NERDM_EXTENSION_SCHEMA_URL],
        "@type": NERDM_DEFAULT_TYPES,
        "@id": paper_id,
        "title": paper.get("title") or paper.get("citation"),
        "contactPoint": {"fn": contact_name} if contact_name else None,
        "modified": _iso_date(paper.get("lastModified")),
        "issued": _iso_date(paper.get("pubDate")),
        "status": "available",
        "landingPage": landing_page,
        "description": description,
        "keyword": keywords,
        "theme": theme,
        "doi": paper.get("doi"),
        "publisher": {"@type": "org:Organization", "name": paper.get("publisher_Info")} if paper.get("publisher_Info") else None,
        "accessLevel": "public"
    }

    return _prune_empty_fields(record)

@router.get("/papers/")
@router.get("/papers")
async def search_papers(request: Request, params: Dict[str, Any] = Depends(validate_search_params)):
    """
    Search papers from the NIST Papers API.
    
    Args:
        params (Dict[str, Any]): Search parameters including:
            - searchphrase (str, optional): Text to search for in papers
            - from_date (str, optional): Start date for search (YYYY-MM-DD)
            - skip (int, optional): Number of results to skip
            - limit (int, optional): Maximum number of results to return
            - include (List[str], optional): Fields to include in results
            - exclude (List[str], optional): Fields to exclude from results
        
    Returns:
        Dict: {
            "ResultData": List of matched papers,
            "ResultCount": Total matches found,
            "PageSize": Number of results per page,
            "Metrics": Query execution metrics
        }
        
    Raises:
        KeyWordNotFoundException: If no papers found matching the criteria
        InternalServerException: If there is an error connecting to the Papers API
        IllegalArgumentException: If the parameters are invalid
    """
    start_time = time.time()
    
    try:
        searchphrase = params.get("searchphrase")
        from_date = params.get("from_date") or params.get("fromDate") or "2010-01-01"
        include = params.get("include")
        exclude = params.get("exclude")

        skip_value = params.get("skip")
        limit_value = params.get("limit") or params.get("size")
        page_value = params.get("page")

        skip = int(skip_value) if skip_value is not None else 0
        limit = int(limit_value) if limit_value is not None else None
        page = int(page_value) if page_value is not None else None

        # Validate parameters
        if include and exclude:
            raise IllegalArgumentException("Cannot use both include and exclude parameters")

        if skip < 0:
            raise IllegalArgumentException("Skip must be non-negative")

        if page is not None and page < 1:
            raise IllegalArgumentException("Page must be at least 1")

        if limit is not None and limit <= 0:
            raise IllegalArgumentException("Limit must be positive when provided")

        if page is not None and skip_value is None:
            if limit is None:
                limit = 10
            skip = (page - 1) * limit
        
        # Check if certificate exists
        if not CERT_PATH.exists():
            logger.error(f"Certificate file not found: {CERT_PATH}")
            raise InternalServerException("Certificate file not found")
            
        verify = str(CERT_PATH)
        
        payload = {
            "searchString": searchphrase if searchphrase else "",
            "fromDate": f"{from_date}T00:00:00.000Z"
        }

        try:
            response = requests.post(
                PAPERS_API_URL,
                json=payload,
                headers=PAPERS_API_HEADERS,
                verify=verify
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Papers API: {str(e)}")
            raise InternalServerException(f"Failed to connect to Papers API: {str(e)}")

        if response.status_code == 200:
            papers_data = response.json()
            
            # If no results were found
            if not papers_data:
                raise KeyWordNotFoundException(str(request.url))
            
            # Map to NERDm-like records, then filter fields and apply pagination
            mapped_data = [map_paper_to_nerdm(paper) for paper in papers_data]
            filtered_data = [
                filter_fields(paper, include, exclude)
                for paper in mapped_data
            ] if mapped_data else []

            if skip or limit is not None:
                end = (skip + limit) if limit is not None else None
                filtered_data = filtered_data[skip:end]
            
            # If pagination results in empty results
            if not filtered_data:
                raise KeyWordNotFoundException(str(request.url))
            
            return {
                "ResultCount": len(papers_data),
                "ResultData": filtered_data,
                "PageSize": limit if limit is not None else 0,
                "Metrics": {"ElapsedTime": time.time() - start_time}
            }
        else:
            logger.error(f"Papers API error: {response.status_code}")
            raise InternalServerException(f"Error from Papers API: {response.status_code}")

    except (KeyWordNotFoundException, IllegalArgumentException, InternalServerException):
        # Re-raise these exceptions for the global exception handlers
        raise
    except Exception as e:
        logger.error(f"Unexpected error in paper search: {str(e)}")
        raise InternalServerException(str(request.url))
