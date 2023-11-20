from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.database.crud import create_new_letter
from app.database.schemas.user import User
from app.main import app
from app.middleware.jwt import decodeJWT

client = TestClient(app)


@pytest.fixture
def register_and_login():
    client.post("/auth/register", json={"name": "John Terry", "email": "johnterry@gmail.com", "password": "password"})
    loginResponse = client.post("/auth/login", json={"email": "johnterry@gmail.com", "password": "password"})
    data = loginResponse.json()
    # get the access token and then decode it
    token = data["access_token"]
    decoded_token = decodeJWT(token)
    user_id = decoded_token["user_id"]
    return token, user_id


def delete_user(user_id):
    user = User.objects(id=user_id).first()

    if user:
        user.delete()
    else:
        # Handle the case where the user with the specified ID is not found
        print(f"User with ID {user_id} not found.")


@pytest.fixture
def insert_treatment_plan(register_and_login):
    token, user_id = register_and_login
    # letter_id = "64dceaf941371bcccfaa5978"
    consent_letter = "<p>4 Privat Drive,<br>Little Whinging,<br>Surrey,<br>CR3 OBD</p><p></p><p>Dear Harry Potter,</p><p></p><p>Further to your recent appointment at which we discussed your treatment options, I have reviewed your symptoms and would like to propose a treatment plan for your dental concerns.</p><p></p><p>Based on your symptoms, it appears that you are experiencing toothache and have noticed some dark spots on one of your teeth during a routine checkup. After considering your responses to the questions, I recommend the following treatment plan:</p><p></p><p>Treatment for Toothache:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to evaluate the extent of the problem</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Root canal treatment if the tooth can be saved</p></li><li><p>Extraction of the tooth if it cannot be saved</p></li></ul></li><li><p>Prescription of pain relief medication, if necessary</p></li></ul><p></p><p>Treatment for Cavity:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to determine the extent of the cavity</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Removal of the decayed portion of the tooth and placement of a dental filling</p></li><li><p>In more severe cases, a dental crown may be recommended</p></li></ul></li><li><p>Recommendation for improved oral hygiene routine and regular dental checkups</p></li></ul><p></p><p>Please note that the proposed treatment plan is subject to a thorough examination and may be adjusted based on the findings during the appointment. It is important to address these dental concerns to prevent further complications and maintain your oral health.</p><p></p><p>If you have any questions or concerns regarding the proposed treatment plan, please do not hesitate to contact our dental practice. We are here to provide you with the necessary information and support to make informed decisions about your dental care.</p><p></p><p>We look forward to seeing you at your next appointment to discuss the treatment plan in more detail and address any additional questions or concerns you may have.</p><p></p><p>Yours sincerely,</p>"
    patient_details = '{"forename": "Harry", "surname": "Potter", "dob": "1905-01-01", "gender": "Male", "address": "4 Privat drive"}'

    for _i in range(0, 4):
        create_new_letter(user_id, consent_letter, patient_details)

    return token


def test_successful_profile_get(insert_treatment_plan):
    token = insert_treatment_plan
    response = client.get(
        "/profile/",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["letters"]) == 3
    assert data["user"]["email"] == "johnterry@gmail.com"


def test_profile_when_user_is_none(insert_treatment_plan):
    token = insert_treatment_plan
    decoded_token = decodeJWT(token)
    user_id = decoded_token["user_id"]
    delete_user(user_id)

    response = client.get(
        "/profile/",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 404, response.text
    data = response.json()
    assert data["detail"] == "User not found"


def test_save_img(insert_treatment_plan):
    token = insert_treatment_plan
    # Simulate an image file
    image_data = Image.new("RGB", (100, 100)).tobytes()

    # Upload image data as multipart form data
    files = {"file": ("image.jpg", BytesIO(image_data), "image/jpeg")}

    response = client.post(
        "/profile/saveImg",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        files=files,
    )

    assert response.status_code == 200, response.text
    assert "image" in response.json()
    assert response.json()["image"]


def test_save_when_img_none(insert_treatment_plan):
    token = insert_treatment_plan

    response = client.post(
        "/profile/saveImg",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        files={},
    )

    assert response.status_code == 400, response.text
    data = response.json()
    assert data["detail"] == "No image data provided"


def test_save_details(insert_treatment_plan):
    token = insert_treatment_plan
    response = client.post(
        "/profile/saveDetails",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"email": "johnterry@aol.com", "phone": "999", "address": "1 Stamford Bridge London"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "johnterry@aol.com"
    assert data["phone"] == "999"
    assert data["address"] == "1 Stamford Bridge London"


def test_save_details_no_data(insert_treatment_plan):
    token = insert_treatment_plan
    response = client.post(
        "/profile/saveDetails",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"email": "", "phone": "", "address": ""},
    )

    assert response.status_code == 400, response.text
    data = response.json()
    assert data["detail"] == "No data provided"
