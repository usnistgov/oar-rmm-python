from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
import os
import requests
import json
import logging
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Construct the absolute path to the .env file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    CONFIG_SOURCE: str = "local"
    # Main database settings
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME: str = os.getenv("DB_NAME", "oar-rmm")
    MONGO_USER: str = os.getenv("MONGO_USER", "")
    MONGO_PASSWORD: str = os.getenv("MONGO_PASSWORD", "")
    MONGO_HOST: str = os.getenv("MONGO_HOST", "localhost")
    MONGO_PORT: int = int(os.getenv("MONGO_PORT", "27017"))

    MONGO_RW_USER: str = os.getenv("MONGO_RW_USER", "")
    MONGO_RW_PASSWORD: str = os.getenv("MONGO_RW_PASSWORD", "")
    MONGO_ADMIN_USER: str = os.getenv("MONGO_ADMIN_USER", "")
    MONGO_ADMIN_PASSWORD: str = os.getenv("MONGO_ADMIN_PASSWORD", "")
    
    # Metrics database settings
    MONGO_URI_METRICS: str = os.getenv("MONGO_URI_METRICS", "")  # Empty string to use same URI as main db
    METRICS_DB_NAME: str = os.getenv("METRICS_DB_NAME", "oar-rmm-metrics")
    METRICS_MONGO_USER: str = os.getenv("METRICS_MONGO_USER", "")
    METRICS_MONGO_PASSWORD: str = os.getenv("METRICS_MONGO_PASSWORD", "")
    METRICS_MONGO_HOST: str = os.getenv("METRICS_MONGO_HOST", "")
    METRICS_MONGO_PORT: int = int(os.getenv("METRICS_MONGO_PORT", "0"))
    
    # Collection names
    RECORDS_COLLECTION: str = os.getenv("RECORDS_COLLECTION", "records")
    TAXONOMY_COLLECTION: str = os.getenv("TAXONOMY_COLLECTION", "taxonomy")
    RESOURCES_COLLECTION: str = os.getenv("RESOURCES_COLLECTION", "apis")
    FIELDS_COLLECTION: str = os.getenv("FIELDS_COLLECTION", "fields")
    RECORD_METRICS_COLLECTION: str = os.getenv("RECORD_METRICS_COLLECTION", "recordMetrics")
    FILE_METRICS_COLLECTION: str = os.getenv("FILE_METRICS_COLLECTION", "fileMetrics")
    UNIQUE_USERS_COLLECTION: str = os.getenv("UNIQUE_USERS_COLLECTION", "uniqueUsers")
    REPO_METRICS_COLLECTION: str = os.getenv("REPO_METRICS_COLLECTION", "repoMetrics")
    VERSIONS_COLLECTION: str = os.getenv("VERSIONS_COLLECTION", "versions")
    RELEASESETS_COLLECTION: str = os.getenv("RELEASESETS_COLLECTION", "releaseSets")
    
    # Remote Configuration
    USE_REMOTE_CONFIG: bool = os.getenv("USE_REMOTE_CONFIG", "False").lower() == "true"
    REMOTE_CONFIG_URL: Optional[str] = os.getenv("REMOTE_CONFIG_URL")

    # Local File Configuration
    LOCAL_CONFIG_FILE: Optional[str] = os.getenv("LOCAL_CONFIG_FILE")
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        
    def show_config_source(self):
        """Print the source of the current configuration"""
        logger.info(f"Configuration source: {self.CONFIG_SOURCE}")
        return self.CONFIG_SOURCE
    
    def dump_config(self, hide_secrets=True):
        """
        Print all current configuration values
        
        Args:
            hide_secrets: If True, password fields will be masked
        """
        logger.info("Current configuration values:")
        for key, value in self.__dict__.items():
            # Mask password fields if hide_secrets is True
            if hide_secrets and "password" in key.lower():
                logger.info(f"  {key}: ********")
            else:
                logger.info(f"  {key}: {value}")

    @classmethod
    def _parse_remote_json(cls, config_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the remote configuration JSON into a flat dictionary with environment variable keys
        
        Args:
            config_json: Nested JSON configuration from remote source
            
        Returns:
            Dict with flattened configuration keys and values
        """
        result = {}
        
        # Map from Java-style keys to Python settings names
        key_mapping = {
            "oar.mongodb.read.user": "MONGO_USER",
            "oar.mongodb.read.password": "MONGO_PASSWORD",
            "oar.mongodb.port": "MONGO_PORT",
            "oar.mongodb.host": "MONGO_HOST",
            "oar.mongodb.database.name": "DB_NAME",
            "oar.metrics.mongodb.port": "METRICS_MONGO_PORT",
            "oar.metrics.mongodb.host": "METRICS_MONGO_HOST",
            "oar.metrics.mongodb.database.name": "METRICS_DB_NAME",
            "oar.mongodb.readwrite.user": "MONGO_RW_USER",
            "oar.mongodb.readwrite.password": "MONGO_RW_PASSWORD",
            "oar.mongodb.admin.user": "MONGO_ADMIN_USER",
            "oar.mongodb.admin.password": "MONGO_ADMIN_PASSWORD",
            "dbcollections.records": "RECORDS_COLLECTION",
            "dbcollections.taxonomy": "TAXONOMY_COLLECTION",
            "dbcollections.resources": "RESOURCES_COLLECTION", 
            "dbcollections.recordfields": "FIELDS_COLLECTION",
            "dbcollections.recordMetrics": "RECORD_METRICS_COLLECTION",
            "dbcollections.fileMetrics": "FILE_METRICS_COLLECTION",
            "dbcollections.uniqueUsers": "UNIQUE_USERS_COLLECTION",
            "dbcollections.repoMetrics": "REPO_METRICS_COLLECTION",
            "dbcollections.versions": "VERSIONS_COLLECTION",
            "dbcollections.releasesets": "RELEASESETS_COLLECTION"
        }
        
        # Extract values from nested JSON
        for java_key, python_key in key_mapping.items():
            parts = java_key.split('.')
            value = config_json
            
            try:
                # Navigate through nested dictionaries
                for part in parts:
                    value = value.get(part, {})
                
                # Only set if we found a non-dictionary value
                if value and not isinstance(value, dict):
                    result[python_key] = value
            except (AttributeError, KeyError):
                # If key doesn't exist or path is invalid, continue to next mapping
                pass
        
        # Construct URIs from components
        if "MONGO_HOST" in result and "MONGO_PORT" in result:
            user_part = ""
            if "MONGO_ADMIN_USER" in result and "MONGO_PASSWORD" in result:
                user_part = f"{result['MONGO_ADMIN_USER']}:{result['MONGO_ADMIN_PASSWORD']}@"
            
            result["MONGO_URI"] = f"mongodb://{user_part}{result['MONGO_HOST']}:{result['MONGO_PORT']}/?authSource=admin"
        
        if "METRICS_MONGO_HOST" in result and "METRICS_MONGO_PORT" in result:
            user_part = ""
            if "METRICS_MONGO_USER" in result and "METRICS_MONGO_PASSWORD" in result:
                user_part = f"{result['METRICS_MONGO_USER']}:{result['METRICS_MONGO_PASSWORD']}@"
                
            result["MONGO_URI_METRICS"] = f"mongodb://{user_part}{result['METRICS_MONGO_HOST']}:{result['METRICS_MONGO_PORT']}/?authSource=admin"

        if "MONGO_PORT" in result:
            try:
                result["MONGO_PORT"] = int(result["MONGO_PORT"])
            except ValueError:
                logger.warning(f"Invalid MONGO_PORT: {result['MONGO_PORT']}, using default")
                result["MONGO_PORT"] = 27017

        if "METRICS_MONGO_PORT" in result:
            try:
                result["METRICS_MONGO_PORT"] = int(result["METRICS_MONGO_PORT"])
            except ValueError:
                logger.warning(f"Invalid METRICS_MONGO_PORT: {result['METRICS_MONGO_PORT']}, using default")
                result["METRICS_MONGO_PORT"] = 27017
        
        logger.info(f"Using MongoDB Host: {result['MONGO_HOST']}, Port: {result['MONGO_PORT']}")
        logger.info(f"Using Username: {result['MONGO_USER']}")  # Don't log the password
        logger.info(f"Constructed MONGO_URI: {result['MONGO_URI'].replace(result['MONGO_PASSWORD'], '********')}")
        return result

    @classmethod
    def from_remote_url(cls, remote_url: str) -> 'Settings':
        """
        Load configuration from a remote URL
        
        Args:
            remote_url: URL to fetch configuration from
            
        Returns:
            Settings object with values from the remote configuration
        """
        try:
            logger.info(f"Loading configuration from remote URL: {remote_url}")
            response = requests.get(remote_url)
            response.raise_for_status()
            
            # Check if the response is Spring Cloud Config format
            data = response.json()
            config_dict = {}
            
            if 'propertySources' in data:
                # Spring Cloud Config format
                if len(data['propertySources']) < 1:
                    logger.warning(f"No configuration data found at {remote_url}")
                    return cls()
                    
                config = {}
                if len(data['propertySources']) > 1:
                    # Load default data first
                    config = data['propertySources'][1].get('source', {})
                
                # Override with specific config
                config.update(data['propertySources'][0].get('source', {}))
                
                # Convert flat dot notation to nested JSON
                nested_config = {}
                for key, value in config.items():
                    parts = key.split('.')
                    current = nested_config
                    
                    # Navigate to the right level
                    for i, part in enumerate(parts):
                        if i == len(parts) - 1:
                            # Last part is the actual key
                            current[part] = value
                        else:
                            if part not in current:
                                current[part] = {}
                            current = current[part]
                
                # Parse the nested config into our settings format
                config_dict = cls._parse_remote_json(nested_config)
            else:
                # Regular JSON format
                config_dict = cls._parse_remote_json(data)
            
            # Create settings with environment vars as defaults, then override with remote config
            settings = cls()
            for key, value in config_dict.items():
                setattr(settings, key, value)
            
            settings.CONFIG_SOURCE = f"remote:{remote_url}"
            logger.info(f"Successfully loaded configuration from {remote_url}")
            
            # Log a few key config values as confirmation
            logger.info(f"Remote config values: DB_NAME={settings.DB_NAME}, MONGO_HOST={settings.MONGO_HOST}")
                
            return settings
            
        except requests.RequestException as e:
            logger.error(f"Network error loading remote config: {type(e).__name__}: {str(e)}")
            logger.info("Using default configuration due to network error")
            return cls()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in remote config: {str(e)}")
            logger.info("Using default configuration due to invalid JSON")
            return cls()
        except Exception as e:
            logger.error(f"Failed to load configuration from {remote_url}: {type(e).__name__}: {str(e)}")
            logger.info("Using default configuration due to unexpected error")
            return cls()
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Settings':
        """Load configuration from a local JSON file"""
        try:
            logger.info(f"Loading configuration from file: {file_path}")
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Create settings with environment vars as defaults
            settings = cls()
            
            # Process the loaded JSON the same way we handle remote config
            config_dict = cls._parse_remote_json(data)
            for key, value in config_dict.items():
                setattr(settings, key, value)
                
            return settings
        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {str(e)}")
            logger.info("Using default configuration")
            return cls()

    @classmethod
    def load(cls) -> 'Settings':
        """
        Load settings from environment or remote URL based on configuration
        
        Returns:
            Settings object with appropriate configuration
        """
        use_remote = os.getenv("USE_REMOTE_CONFIG", "false").lower() == "true"
        remote_url = os.getenv("REMOTE_CONFIG_URL")
        local_file = os.getenv("LOCAL_CONFIG_FILE")
        
        if use_remote and remote_url:
            return cls.from_remote_url(remote_url)
        elif local_file and os.path.exists(local_file):
            settings = cls.from_file(local_file)
            settings.CONFIG_SOURCE = f"file:{local_file}"
            return settings
        else:
            settings = cls()
            settings.CONFIG_SOURCE = "environment"
            logger.info("Using configuration from environment variables")
            return settings



# Diagnostic logging
logger.info("=== Configuration Diagnostics ===")
logger.info(f"USE_REMOTE_CONFIG env var: {os.getenv('USE_REMOTE_CONFIG')}")
logger.info(f"REMOTE_CONFIG_URL env var: {os.getenv('REMOTE_CONFIG_URL')}")
logger.info(f".env file location: {dotenv_path}")
logger.info(f".env file exists: {os.path.exists(dotenv_path)}")
logger.info("================================")
# Create the settings instance
settings = Settings.load()

# Show configuration source
settings.show_config_source()

# Log configuration details
logger.info(f"Database Configuration:")
logger.info(f"  MONGO_URI: {settings.MONGO_URI}")
logger.info(f"  DB_NAME: {settings.DB_NAME}")

# Log metrics database configuration if available
if settings.MONGO_URI_METRICS:
    logger.info(f"Metrics Database Configuration:")
    logger.info(f"  MONGO_URI_METRICS: {settings.MONGO_URI_METRICS}")
    logger.info(f"  METRICS_DB_NAME: {settings.METRICS_DB_NAME}")
else:
    logger.info("Metrics database using same connection as main database")