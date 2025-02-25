import requests
import logging
from datetime import datetime
from app.database import db
from app.crud.code import code_crud

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CODE_API_URL = "https://code.nist.gov/explore/code.json"

def fetch_code_data():
    """Fetch code data from NIST API"""
    try:
        response = requests.get(CODE_API_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch code data: {e}")
        return None

def transform_release(release):
    """Transform a release into the desired document structure"""
    return {
        "name": release.get("name", ""),
        "organization": release.get("organization", ""),
        "description": release.get("description", ""),
        "repositoryURL": release.get("repositoryURL", ""),
        "homepageURL": release.get("homepageURL", ""),
        "downloadURL": release.get("downloadURL", ""),
        "languages": release.get("languages", []),
        "contact": {
            "email": release.get("contact", {}).get("email", ""),
            "url": release.get("contact", {}).get("URL", "")
        },
        "dates": {
            "created": release.get("date", {}).get("created", ""),
            "lastModified": release.get("date", {}).get("lastModified", "")
        },
        "permissions": {
            "usageType": release.get("permissions", {}).get("usageType", ""),
            "licenses": release.get("permissions", {}).get("licenses", [])
        },
        "status": release.get("status", ""),
        "laborHours": release.get("laborHours", 0),
        "tags": release.get("tags", []),
        "vcs": release.get("vcs", "")
    }

def populate_code_collection():
    """Populate code collection with data from NIST API"""
    try:
        # Clear existing data
        db.code.drop()
        logger.info("Dropped existing code collection")
        
        # Create text index
        db.code.create_index([("$**", "text")])
        logger.info("Created text index for code collection")
        
        # Fetch data
        data = fetch_code_data()
        if not data or not isinstance(data, dict):
            logger.error("Invalid data format received")
            return False
            
        # Process releases
        releases = data.get("releases", [])
        success_count = 0
        
        for release in releases:
            try:
                if release.get("name"):  # Only process entries with names
                    transformed_data = transform_release(release)
                    code_crud.create(transformed_data)
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to process release {release.get('name')}: {e}")
                continue
                    
        logger.info(f"Successfully populated code collection with {success_count} entries")
        return True
        
    except Exception as e:
        logger.error(f"Failed to populate code collection: {e}")
        return False

if __name__ == "__main__":
    populate_code_collection()