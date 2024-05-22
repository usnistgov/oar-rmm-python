from fastapi.testclient import TestClient
from app.main import app
import json
import pytest

client = TestClient(app)

try:
    with open("./record.json") as file:
        test_record = json.load(file)
except FileNotFoundError:
    pytest.fail("Test record file not found!")

def test_create_record():
    response = client.post("/records/", json=test_record)
    assert response.status_code == 200
    record = response.json()
    assert record["_id"] == test_record["_id"]
    assert record["@context"] == test_record["@context"]
    assert record["_schema"] == test_record["_schema"]
    assert record["_extensionSchemas"] == test_record["_extensionSchemas"]
    assert record["@type"] == test_record["@type"]
    assert record["@id"] == test_record["@id"]
    assert record["title"] == test_record["title"]
    assert record["contactPoint"] == test_record["contactPoint"]
    assert record["modified"] == test_record["modified"]
    assert record["status"] == test_record["status"]
    assert record["ediid"] == test_record["ediid"]
    assert record["landingPage"] == test_record["landingPage"]
    assert record["description"] == test_record["description"]
    assert record["keyword"] == test_record["keyword"]
    assert record["theme"] == test_record["theme"]
    assert record["topic"] == test_record["topic"]
    assert record["references"] == test_record["references"]
    assert record["accessLevel"] == test_record["accessLevel"]
    assert record["license"] == test_record["license"]
    assert record["inventory"] == test_record["inventory"]
    assert record["components"] == test_record["components"]
    assert record["publisher"] == test_record["publisher"]
    assert record["language"] == test_record["language"]
    assert record["bureauCode"] == test_record["bureauCode"]
    assert record["programCode"] == test_record["programCode"]
    assert record["version"] == test_record["version"]

def test_read_records():
    response = client.get("/records/")
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    if records:  # if the list is not empty
        record = records[0]
        assert record["_id"] == test_record["_id"]
        assert record["@context"] == test_record["@context"]
        assert record["_schema"] == test_record["_schema"]
        assert record["_extensionSchemas"] == test_record["_extensionSchemas"]
        assert record["@type"] == test_record["@type"]
        assert record["@id"] == test_record["@id"]
        assert record["title"] == test_record["title"]
        assert record["contactPoint"] == test_record["contactPoint"]
        assert record["modified"] == test_record["modified"]
        assert record["status"] == test_record["status"]
        assert record["ediid"] == test_record["ediid"]
        assert record["landingPage"] == test_record["landingPage"]
        assert record["description"] == test_record["description"]
        assert record["keyword"] == test_record["keyword"]
        assert record["theme"] == test_record["theme"]
        assert record["topic"] == test_record["topic"]
        assert record["references"] == test_record["references"]
        assert record["accessLevel"] == test_record["accessLevel"]
        assert record["license"] == test_record["license"]
        assert record["inventory"] == test_record["inventory"]
        assert record["components"] == test_record["components"]
        assert record["publisher"] == test_record["publisher"]
        assert record["language"] == test_record["language"]
        assert record["bureauCode"] == test_record["bureauCode"]
        assert record["programCode"] == test_record["programCode"]
        assert record["version"] == test_record["version"]