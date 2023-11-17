import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app.constants import JWT_ALGORITHM, SECRET_KEY, TEST_DB_URI
from app.database.db import connect_to_mongodb
from app.main import app
from app.middleware.jwt import decodeJWT

app.state.db = connect_to_mongodb(TEST_DB_URI)
client = TestClient(app)


# Hook that wipes users collection after each test finishes
@pytest.fixture(autouse=True)
def cleanup_database(request):
    db = app.state.db

    # Get a list of all collections in the database
    collections = db.list_collection_names()

    # Exclude 'configs' collection from the list
    collections_to_drop = [collection_name for collection_name in collections if collection_name != "configs"]

    # Drop all collections (except 'configs')
    for collection_name in collections_to_drop:
        if collection_name != "system.indexes":  # Skip system.indexes collection
            db[collection_name].drop()

    # Run all tests
    yield

    # Drop all collections (except 'configs')
    for collection_name in collections_to_drop:
        if collection_name != "system.indexes":  # Skip system.indexes collection
            db[collection_name].drop()



@pytest.fixture
def register_test_user():
    response = client.post("/auth/register", json={"name": "John Terry", "email": "johnterry@gmail.com", "password": "password"})
    return response


def test_register_user(register_test_user):
    assert register_test_user.status_code == 200, register_test_user.text
    data = register_test_user.json()
    assert data["message"] == "Registered successfully"


def test_register_existing_user(register_test_user):
    response = client.post("/auth/register", json={"name": "John Terry", "email": "johnterry@gmail.com", "password": "password"})

    assert response.status_code == 400, response.text
    data = response.json()
    assert data["detail"] == "Email already in use"


def test_login_user(register_test_user):
    response = client.post("/auth/login", json={"email": "johnterry@gmail.com", "password": "password"})

    # Checks if response was success
    assert response.status_code == 200, response.text
    data = response.json()

    # get the access token and then decode it
    token = data["access_token"]
    decoded_token = decodeJWT(token)

    # get the user id from the db in order to assert access_token is correct
    db = app.state.db
    users_collection = db["users"]
    user_document = users_collection.find_one({"email": "johnterry@gmail.com"})
    user_id = str(user_document["_id"])
    assert decoded_token["user_id"] == user_id


def test_login_user_access_denied():
    response = client.post("/auth/login", json={"email": "johnterry@gmail.com", "password": "incorrectPassword"})

    assert response.status_code == 403, response.text
    data = response.json()
    assert data["detail"] == "Access denied."


def test_authenticate_user(register_test_user):
    loginResponse = client.post("/auth/login", json={"email": "johnterry@gmail.com", "password": "password"})

    data = loginResponse.json()
    token = data["access_token"]

    response = client.get(
        "/auth/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.text


def test_authenticate_user_incorrect_token(register_test_user):
    response = client.get(
        "/auth/user",
        headers={
            "Authorization": "None",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 403, response.text


def test_decodeJWT_expired_signature():
    # Create an expired token to test the ExpiredSignatureError
    expired_token = jwt.encode({"data": "sample_data", "expires": time.time() - 1000}, SECRET_KEY, algorithm=JWT_ALGORITHM)
    decoded_token = decodeJWT(expired_token)
    # Ensure the function returns None for an expired token
    assert decoded_token is None


def test_decodeJWT_invalid_token():
    # Create an invalid token to test the InvalidTokenError
    invalid_token = "invalid_token_string"

    # Ensure the function returns None for an invalid token
    assert decodeJWT(invalid_token) is None


def test_invalid_authentication_scheme(register_test_user):
    loginResponse = client.post("/auth/login", json={"email": "johnterry@gmail.com", "password": "password"})

    data = loginResponse.json()
    token = data["access_token"]

    response = client.get(
        "/auth/user",
        headers={
            "Authorization": f"NotBearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 403, response.text
    data = response.json()
    assert data["detail"] == "Invalid authentication credentials"


def test_expired_token(register_test_user):
    expired_token = jwt.encode({"data": "sample_data", "expires": time.time() - 1000}, SECRET_KEY, algorithm=JWT_ALGORITHM)

    response = client.get(
        "/auth/user",
        headers={
            "Authorization": f"Bearer {expired_token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 403, response.text
    data = response.json()
    assert data["detail"] == "Invalid token or expired token."


def test_no_token(register_test_user):
    response = client.get(
        "/auth/user",
        headers={
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 403, response.text
    data = response.json()
    assert data["detail"] == "Not authenticated"
