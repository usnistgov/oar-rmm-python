from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.MONGO_URI)
db_name = settings.DB_NAME
db = client[db_name]

# Create a new text index on the `title`, `description`, and other relevant fields
db.records.create_index(
    [("title", "text"), ("description", "text"), ("keyword", "text"), ("theme", "text"), ("topic", "text"), ("contactPoint.fn", "text"), ("contactPoint.hasEmail", "text"), ("landingPage", "text")],
    default_language="english",
    language_override="lang"
)

# Create additional indexes on other relevant fields for search
db.records.create_index([("keyword", 1)])
db.records.create_index([("theme", 1)])
db.records.create_index([("topic", 1)])
db.records.create_index([("contactPoint.fn", 1)])
db.records.create_index([("contactPoint.hasEmail", 1)])
db.records.create_index([("landingPage", 1)])
db.records.create_index([("ediid", 1)])
db.records.create_index([("modified", 1)])
db.records.create_index([("status", 1)])
db.fields.create_index([("tags", 1)])

print('Database connection established and indexes created.', flush=True)