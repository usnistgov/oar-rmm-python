#!/usr/bin/env python3
"""Manual/pytest-compatible connectivity check for the configured MongoDB instance.

Provides both a pytest-style assertion-based test (:func:`test_connection`)
and a command-line entry point (:func:`main`) that report the configured
Mongo URI (with the password masked), confirm a successful connection, and
list the available collections.
"""
import sys
import logging
import pymongo
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    """Assert that a connection to the configured MongoDB database succeeds.

    Pytest-discoverable test function (name starts with ``test_``). Logs the
    masked connection URI, database name, and list of collections found.

    Raises:
        AssertionError: If the connection attempt raises any exception.
    """
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
    """Command-line entry point: verify the MongoDB connection and print diagnostics.

    Returns:
        bool: ``True`` if the connection succeeded, ``False`` otherwise. The
        ``if __name__ == "__main__"`` block converts this to a process exit
        code (0 for success, 1 for failure).
    """
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