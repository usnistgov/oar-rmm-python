from typing import Optional
from pydantic_settings import BaseSettings
import os
import requests
from dotenv import load_dotenv

# Construct the absolute path to the .env file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, '.env')  # Adjust the path as needed
print(f"Loading .env file from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)  # Load the specified .env file

class Settings(BaseSettings):
    MONGO_URI: str
    DB_NAME: str
    USE_REMOTE_CONFIG: bool = False
    REMOTE_CONFIG_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

    @classmethod
    def from_remote(cls):
        remote_config_url = os.getenv("REMOTE_CONFIG_URL")
        if not remote_config_url:
            raise ValueError("REMOTE_CONFIG_URL is not set.")
        response = requests.get(remote_config_url)
        response.raise_for_status()
        config = response.json()
        return cls(**config)

    @classmethod
    def load(cls):
        if os.getenv("USE_REMOTE_CONFIG", "false").lower() == "true":
            return cls.from_remote()
        return cls()

settings = Settings.load()

print(f"MONGO_URI: {settings.MONGO_URI}")
print(f"DB_NAME: {settings.DB_NAME}")