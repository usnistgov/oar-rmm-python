import time
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
metrics_client = None
metrics_db = None

# Define collection names from settings for easier access
main_collections = [
    settings.RECORDS_COLLECTION,
    settings.TAXONOMY_COLLECTION,
    settings.RESOURCES_COLLECTION,
    settings.FIELDS_COLLECTION,
    settings.VERSIONS_COLLECTION,
    settings.RELEASESETS_COLLECTION
]

metrics_collections = [
    settings.RECORD_METRICS_COLLECTION,
    settings.FILE_METRICS_COLLECTION,
    settings.UNIQUE_USERS_COLLECTION,
    settings.REPO_METRICS_COLLECTION
]

def connect_db():
    """Connect to MongoDB and return the database instance"""
    global client, db
    
    retry_count = 3
    for attempt in range(retry_count):
        try:
            # Connect to MongoDB
            logger.info(f"Connecting to MongoDB: {settings.MONGO_URI}")
            client = MongoClient(settings.MONGO_URI)
            db = client[settings.DB_NAME]
            
            # Test the connection
            client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {settings.DB_NAME}")
            return db
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB (attempt {attempt+1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                logger.info(f"Retrying in 2 seconds...")
                time.sleep(2)
            else:
                raise InternalServerException(f"Database connection error: {str(e)}")
            
def connect_metrics_db():
    """Connect to metrics MongoDB and return the database instance"""
    global metrics_client, metrics_db
    
    try:
        # Use metrics URI if provided, otherwise fall back to main URI
        metrics_uri = settings.MONGO_URI_METRICS or settings.MONGO_URI
        metrics_db_name = settings.METRICS_DB_NAME
        
        # Use the same client if connecting to the same server
        if metrics_uri == settings.MONGO_URI and client:
            metrics_client = client
            metrics_db = client[metrics_db_name]
        else:
            metrics_client = MongoClient(metrics_uri)
            metrics_db = metrics_client[metrics_db_name]
            
        # Test the connection
        metrics_client.admin.command('ping')
        logger.info(f"Connected to Metrics MongoDB: {metrics_db_name}")
        return metrics_db
    except Exception as e:
        logger.error(f"Failed to connect to Metrics MongoDB: {e}")
        raise InternalServerException(f"Metrics database connection error: {str(e)}")

def create_text_index(collection_name, database=None):
    """Create text index for a collection with error handling"""
    try:
        target_db = database or db
        if collection_name not in target_db.list_collection_names():
            # Collection doesn't exist yet, will be created when data is inserted
            logger.warning(f"Collection {collection_name} doesn't exist yet. Index will be created when data is added.")
            return True
        
        collection = target_db[collection_name]
        collection.create_index([("$**", TEXT)])
        logger.info(f"Created text index for {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Error creating text index for {collection_name}: {e}")
        return False

def create_collection_indexes():
    """
    Create indexes for all collections with improved error handling.
    
    NOTE: This function is NOT automatically called in production environments.
    Indexes are managed by an external container in the Docker setup.
    """
    try:
        success = True
        
        # Create text indexes for all collections
        for collection in main_collections:
            success = create_text_index(collection) and success
            
            try:
                if collection == settings.FIELDS_COLLECTION:
                    db[settings.FIELDS_COLLECTION].create_index([("name", ASCENDING)])
                    db[settings.FIELDS_COLLECTION].create_index([("searchable", ASCENDING)])
                    logger.info("Created specific indexes for fields collection")
                elif collection == settings.RESOURCES_COLLECTION:  # APIs
                    db[settings.RESOURCES_COLLECTION].create_index([("name", ASCENDING)])
                    db[settings.RESOURCES_COLLECTION].create_index([("apiUrl", ASCENDING)])
                    logger.info("Created specific indexes for APIs collection")
                elif collection == settings.RECORDS_COLLECTION:
                    db[settings.RECORDS_COLLECTION].create_index([("doi", ASCENDING)])
                    db[settings.RECORDS_COLLECTION].create_index([("ediid", ASCENDING)])
                    logger.info("Created specific indexes for records collection")
                    
            except Exception as e:
                logger.error(f"Error creating indexes for {collection}: {e}")
                success = False
                # Continue with next collection instead of failing completely
        
        # Create indexes for metrics collections
        try:
            # recordMetrics collection indexes
            if settings.RECORD_METRICS_COLLECTION in metrics_db.list_collection_names():
                metrics_db[settings.RECORD_METRICS_COLLECTION].create_index([("pdrid", ASCENDING)], background=True)
                metrics_db[settings.RECORD_METRICS_COLLECTION].create_index([("ediid", ASCENDING)], background=True)
                metrics_db[settings.RECORD_METRICS_COLLECTION].create_index([("first_time_logged", ASCENDING)], background=True)
                metrics_db[settings.RECORD_METRICS_COLLECTION].create_index([("last_time_logged", ASCENDING)], background=True)
                logger.info(f"Created indexes for {settings.RECORD_METRICS_COLLECTION} collection")
            else:
                logger.warning(f"{settings.RECORD_METRICS_COLLECTION} collection doesn't exist yet. Indexes will be created when data is added.")
            
            # fileMetrics collection indexes
            if settings.FILE_METRICS_COLLECTION in metrics_db.list_collection_names():
                metrics_db[settings.FILE_METRICS_COLLECTION].create_index([("ediid", ASCENDING)], background=True)
                metrics_db[settings.FILE_METRICS_COLLECTION].create_index([("filepath", ASCENDING)], background=True)
                metrics_db[settings.FILE_METRICS_COLLECTION].create_index([("last_time_logged", ASCENDING)], background=True)
                logger.info(f"Created indexes for {settings.FILE_METRICS_COLLECTION} collection")
            else:
                logger.warning(f"{settings.FILE_METRICS_COLLECTION} collection doesn't exist yet. Indexes will be created when data is added.")
            
            # repoMetrics collection indexes
            if settings.REPO_METRICS_COLLECTION in metrics_db.list_collection_names():
                metrics_db[settings.REPO_METRICS_COLLECTION].create_index([("month", ASCENDING)], background=True)
                metrics_db[settings.REPO_METRICS_COLLECTION].create_index([("year", ASCENDING)], background=True)
                logger.info(f"Created indexes for {settings.REPO_METRICS_COLLECTION} collection")
            else:
                logger.warning(f"{settings.REPO_METRICS_COLLECTION} collection doesn't exist yet. Indexes will be created when data is added.")
            
            # uniqueUsers collection indexes
            if settings.UNIQUE_USERS_COLLECTION in metrics_db.list_collection_names():
                metrics_db[settings.UNIQUE_USERS_COLLECTION].create_index([("date", ASCENDING)], background=True)
                metrics_db[settings.UNIQUE_USERS_COLLECTION].create_index([("year", ASCENDING), ("month", ASCENDING)], background=True)
                logger.info(f"Created indexes for {settings.UNIQUE_USERS_COLLECTION} collection")
            else:
                logger.warning(f"{settings.UNIQUE_USERS_COLLECTION} collection doesn't exist yet. Indexes will be created when data is added.")
                
        except Exception as e:
            logger.error(f"Error creating metrics indexes: {e}")
            success = False
            # Don't fail the entire process if metrics indexes fail
        
        return success
        
    except Exception as e:
        logger.error(f"Error in create_collection_indexes: {e}")
        return False

# Pre-connect during import for simpler usage elsewhere
db = connect_db()
metrics_db = connect_metrics_db()

# Don't create indexes automatically - this is handled by another container
# index_result = create_collection_indexes()