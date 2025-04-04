#!/usr/bin/env python3
import time
import logging
import sys
import os
import pymongo

# Add the project root directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../.."))
sys.path.insert(0, project_root)

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_mongodb():
    """Wait for MongoDB to become available with proper authentication"""
    max_attempts = 30
    delay_seconds = 2
    
    # Check main database first
    logger.info(f"Waiting for main MongoDB to be ready at {settings.MONGO_URI}")
    logger.info(f"Using DB: {settings.DB_NAME}")
    
    if not test_connection(settings.MONGO_URI, settings.DB_NAME, max_attempts, delay_seconds):
        return False
    
    # Then check metrics database if configured separately
    metrics_uri = settings.MONGO_URI_METRICS or settings.MONGO_URI
    if metrics_uri != settings.MONGO_URI:
        logger.info(f"Waiting for metrics MongoDB to be ready at {metrics_uri}")
        logger.info(f"Using metrics DB: {settings.METRICS_DB_NAME}")
        
        if not test_connection(metrics_uri, settings.METRICS_DB_NAME, max_attempts, delay_seconds):
            return False
    
    return True

def test_connection(mongo_uri, db_name, max_attempts, delay_seconds):
    """Test connection to a specific MongoDB instance"""
    for attempt in range(max_attempts):
        try:
            # Try connection without auth first to see if server is up
            no_auth_uri = mongo_uri.split('@')[-1]
            no_auth_uri = f"mongodb://{no_auth_uri}"
            
            logger.info(f"Attempt {attempt+1}/{max_attempts}: Testing MongoDB availability")
            client = pymongo.MongoClient(no_auth_uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            logger.info(f"MongoDB server is available")
            client.close()
            
            # Now try with authentication
            logger.info(f"Testing authentication...")
            auth_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            auth_client.admin.command('ping')
            
            # Try to access the specific database
            test_db = auth_client[db_name]
            # Lightweight operation to test actual database access
            _ = test_db.list_collection_names()
            
            auth_client.close()
            
            logger.info(f"Successfully connected to MongoDB with authentication")
            return True
        except pymongo.errors.OperationFailure as e:
            if "Authentication failed" in str(e):
                logger.warning(f"Authentication failed (attempt {attempt+1}/{max_attempts}): {str(e)}")
                time.sleep(delay_seconds)
            else:
                logger.error(f"MongoDB operation error: {str(e)}")
                time.sleep(delay_seconds)
        except Exception as e:
            logger.warning(f"Cannot connect to MongoDB (attempt {attempt+1}/{max_attempts}): {str(e)}")
            time.sleep(delay_seconds)
    
    logger.error(f"Failed to connect to MongoDB at {mongo_uri} after maximum attempts")
    return False