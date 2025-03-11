from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.errors import OperationFailure
from app.config import settings
import logging
from app.middleware.exceptions import InternalServerException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize variables
client = None
db = None

def connect_db():
    """Connect to MongoDB and return the database instance"""
    global client, db
    
    try:
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.DB_NAME]
        # Test the connection
        client.admin.command('ping')
        logger.info(f"Connected to MongoDB: {settings.DB_NAME}")
        return db
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise InternalServerException(f"Database connection error: {str(e)}")

def create_text_index(collection_name):
    """Create text index for a collection with error handling"""
    try:
        # Create text index with language_override option to handle language fields
        db[collection_name].create_index([("$**", "text")], 
                                        language_override="lang")
        logger.info(f"Created text index for {collection_name} collection")
        return True
    except OperationFailure as e:
        # Special handling for language override errors
        if "language override field" in str(e):
            logger.warning(f"Cannot create wildcard text index for {collection_name}: language field issue. Creating basic indexes instead.")
            # Create basic indexes on common fields as a fallback
            try:
                db[collection_name].create_index([("name", ASCENDING)])
                db[collection_name].create_index([("title", ASCENDING)])
                db[collection_name].create_index([("description", ASCENDING)])
                logger.info(f"Created basic indexes for {collection_name} collection")
                return True
            except Exception as inner_e:
                logger.error(f"Failed to create basic indexes for {collection_name}: {inner_e}")
                return False
        else:
            logger.error(f"Failed to create text index for {collection_name}: {e}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error creating index for {collection_name}: {e}")
        return False

def create_collection_indexes():
    """Create indexes for all collections with improved error handling"""
    failures = []
    
    try:
        # Records collection (with special handling)
        try:
            # Drop existing text indexes
            for index in db.records.list_indexes():
                if 'weights' in index:  # This identifies text indexes
                    db.records.drop_index(index['name'])
                    logger.info(f"Dropped existing text index: {index['name']}")

            # Create new wildcard text index
            db.records.create_index(
                [("$**", "text")],
                language_override="dummy"
            )
            logger.info("Created wildcard text index for records collection")
        except Exception as e:
            failures.append(f"records: {str(e)}")
            logger.error(f"Failed to create index for records: {e}")

        # Create indexes for all other collections
        collections = [
            "fields", "code", "apis", "releasesets", "taxonomy"
        ]
        
        for collection in collections:
            if not create_text_index(collection):
                failures.append(collection)
        
        # Handle versions collection separately due to known issues
        try:
            # Try creating basic indexes instead of text index
            db.versions.create_index([("version", ASCENDING)])
            db.versions.create_index([("name", ASCENDING)])
            logger.info("Created basic indexes for versions collection")
        except Exception as e:
            failures.append(f"versions: {str(e)}")
            logger.error(f"Failed to create indexes for versions collection: {e}")

        if failures:
            logger.warning(f"Some indexes failed to create: {', '.join(failures)}")
            # Don't raise exception to allow application to continue
        
        return True

    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        # Don't raise exception, let the application continue even if indexes fail
        return False

# Pre-connect during import for simpler usage elsewhere
db = connect_db()