from pymongo import MongoClient, ASCENDING, TEXT
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

def create_collection_indexes():
    """Create wildcard text index for all fields"""
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
        logger.info("Created wildcard text index for all fields")

        # Create index for fields collection
        db.fields.create_index([("tags", ASCENDING)])
        logger.info("Created index for fields collection")
        db.code.create_index([("$**", "text")])
        logger.info("Created text index for code collection")

    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise InternalServerException(f"Failed to create database indexes: {str(e)}")

# Pre-connect during import for simpler usage elsewhere
db = connect_db()

# Optional: Create indexes during startup
# create_collection_indexes()