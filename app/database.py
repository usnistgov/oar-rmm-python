from pymongo import MongoClient, ASCENDING, TEXT
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = MongoClient(settings.MONGO_URI)
db_name = settings.DB_NAME
db = client[db_name]

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

    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise

# Create indexes
create_collection_indexes()

print('Database connection established and indexes created.', flush=True)