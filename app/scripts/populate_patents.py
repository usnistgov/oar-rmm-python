import json
import logging
from pathlib import Path
from datetime import datetime
from app.database import db
from app.crud.patent import patent_crud
from app.middleware.exceptions import InternalServerException

logger = logging.getLogger(__name__)

def populate_patents_collection():
    """Populate patents collection with data from JSON file"""
    try:
        # Get path to patents JSON file
        patents_file = Path(__file__).parent.parent / "patents" / "5.8.23.json"
        
        if not patents_file.exists():
            logger.error(f"Patents file not found: {patents_file}")
            raise InternalServerException(f"Patents file not found: {patents_file}")
            
        # Clear existing collection
        db.patents.drop()
        
        # Create indexes
        db.patents.create_index([("$**", "text")])  # Full text search
        db.patents.create_index([("Descriptive Title", 1)])
        db.patents.create_index([("Patent #", 1)])
        db.patents.create_index([("Laboratory 1", 1)])
        db.patents.create_index([("Status", 1)])
        db.patents.create_index([("File Date", 1)])
        
        # Load and insert patents
        with open(patents_file) as f:
            patents = json.load(f)
            
        # Process and insert each patent
        for patent in patents:
            # Convert epoch timestamps to ISO dates
            for date_field in ["File Date", "Patent Issue Date", "Expiration Date", "Publication Date"]:
                if patent.get(date_field):
                    try:
                        timestamp = int(patent[date_field]) / 1000  # Convert milliseconds to seconds
                        patent[date_field] = datetime.fromtimestamp(timestamp).isoformat()
                    except:
                        patent[date_field] = None
                        
            # Insert patent
            patent_crud.create(patent)
            
        logger.info(f"Successfully imported {len(patents)} patents")
        return True
        
    except InternalServerException:
        # Re-raise specific exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to populate patents collection: {e}")
        raise InternalServerException(f"Failed to populate patents collection: {str(e)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    populate_patents_collection()