#!/usr/bin/env python3
import sys
import logging
import pymongo
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    """Test MongoDB connection with current settings"""
    try:
        # Show config details (masking password)
        mongo_uri_masked = settings.MONGO_URI
        if settings.MONGO_PASSWORD:
            mongo_uri_masked = mongo_uri_masked.replace(settings.MONGO_PASSWORD, "********")
        
        logger.info(f"Testing connection to: {mongo_uri_masked}")
        logger.info(f"Database name: {settings.DB_NAME}")
        
        # Try connecting
        client = pymongo.MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[settings.DB_NAME]
        client.admin.command('ping')
        
        # Check collections
        collections = db.list_collection_names()
        logger.info(f"Successfully connected to MongoDB")
        logger.info(f"Available collections: {collections}")
        
        # Use assert instead of return for pytest
        assert True, "Connection successful"
        
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        assert False, f"Connection failed: {str(e)}"

def main():
    """Main function for command line usage"""
    try:
        # Show config details (masking password)
        mongo_uri_masked = settings.MONGO_URI
        if settings.MONGO_PASSWORD:
            mongo_uri_masked = mongo_uri_masked.replace(settings.MONGO_PASSWORD, "********")
        
        logger.info(f"Testing connection to: {mongo_uri_masked}")
        logger.info(f"Database name: {settings.DB_NAME}")
        
        # Try connecting
        client = pymongo.MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[settings.DB_NAME]
        client.admin.command('ping')
        
        # Check collections
        collections = db.list_collection_names()
        logger.info(f"Successfully connected to MongoDB")
        logger.info(f"Available collections: {collections}")
        
        return True
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)