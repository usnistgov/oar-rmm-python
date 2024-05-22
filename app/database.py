from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.MONGO_URI)
db_name = settings.DB_NAME
db = client[db_name]

# Create a text index on the `title` and `description` fields, specifying a custom language override field
db.records.create_index(
    [("title", "text"), ("description", "text")],
    default_language="english",
    language_override="lang"
)