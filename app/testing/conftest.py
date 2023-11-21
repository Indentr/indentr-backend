import pytest
from mongoengine import connect

from app.constants import TEST_DB_URI


# This fixture sets up and tears down the test database for each test
@pytest.fixture(autouse=True)
def cleanup_database(request):
    # Get the MongoDB database reference
    db = connect(host=TEST_DB_URI, uuidRepresentation='unspecified').get_database()

    # Get a list of all collections in the test database
    collections = db.list_collection_names()

    # Exclude 'configs' collection from the list
    collections_to_drop = [collection_name for collection_name in collections if collection_name != "configs"]

    # Drop all collections (except 'configs')
    for collection_name in collections_to_drop:
        if collection_name != "system.indexes":  # Skip system.indexes collection
            db[collection_name].drop()

    # Run tests
    yield
