import pytest
from fastapi.testclient import TestClient

from app.constants import TEST_DB_URI
from app.db import connect_to_mongodb
from app.main import app
from app.middleware.jwt import decodeJWT

success_token = 1
app.state.db = connect_to_mongodb(TEST_DB_URI)
client = TestClient(app)


# Hook that wipes users collection once tests have finished
@pytest.fixture(scope="session", autouse=True)
def cleanup_database(request):
    db = app.state.db

    # Provide the collection name where your user data is stored
    user_collection = db["users"]

    # Run all tests
    yield

    # Perform the cleanup after all tests
    user_collection.delete_many({})  # Clear the user collection


def test_register_user():
    response = client.post("/auth/register", json={"name": "John Terry", "email": "johnterry@gmail.com", "password": "password"})

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["message"] == "Registered successfully"


def test_register_existing_user():
    response = client.post("/auth/register", json={"name": "John Terry", "email": "johnterry@gmail.com", "password": "password"})

    assert response.status_code == 400, response.text
    data = response.json()
    assert data["detail"] == "Email already in use"


def test_login_user():
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


def test_authenticate_user():
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


def test_authenticate_user_incorrect_token():
    response = client.get(
        "/auth/user",
        headers={
            "Authorization": "None",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 403, response.text
