import pytest
from fastapi.testclient import TestClient

from app.database.crud.letter import create_new_letter
from app.database.crud.patient import create_new_patient
from app.database.crud.practice import create_new_practice
from app.database.crud.user import create_new_user
from app.database.schemas.user import User
from app.main import app
from app.middleware.jwt import decodeJWT

client = TestClient(app)


@pytest.fixture
def register_and_login():
    client.post(
        "/auth/register",
        json={
            "name": "John Terry",
            "email": "johnterry@gmail.com",
            "password": "password",
            "practice_name": "Willows Dental",
            "practice_email": "johnterry@willows.com",
            "practice_url": "https://www.willowsdental.com",
            "address": "1 Prestatyn, Wales, W1",
            "phone": "07880788392",
            "gratis_password": "YOUSHALLPASS!",
        },
    )
    loginResponse = client.post("/auth/login", json={"email": "johnterry@gmail.com", "password": "password"})
    data = loginResponse.json()
    # get the access token and then decode it
    token = data["access_token"]
    decoded_token = decodeJWT(token)
    user_id = decoded_token["user_id"]
    practice_id = decoded_token["practice_id"]
    return token, user_id, practice_id


def delete_user(user_id):
    user = User.objects(id=user_id).first()

    if user:
        user.delete()
    else:
        # Handle the case where the user with the specified ID is not found
        print(f"User with ID {user_id} not found.")


@pytest.fixture
def insert_treatment_plan(register_and_login):
    token, user_id, practice_id = register_and_login
    consent_letter = "<p>4 Privat Drive,<br>Little Whinging,<br>Surrey,<br>CR3 OBD</p><p></p><p>Dear Harry Potter,</p><p></p><p>Further to your recent appointment at which we discussed your treatment options, I have reviewed your symptoms and would like to propose a treatment plan for your dental concerns.</p><p></p><p>Based on your symptoms, it appears that you are experiencing toothache and have noticed some dark spots on one of your teeth during a routine checkup. After considering your responses to the questions, I recommend the following treatment plan:</p><p></p><p>Treatment for Toothache:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to evaluate the extent of the problem</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Root canal treatment if the tooth can be saved</p></li><li><p>Extraction of the tooth if it cannot be saved</p></li></ul></li><li><p>Prescription of pain relief medication, if necessary</p></li></ul><p></p><p>Treatment for Cavity:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to determine the extent of the cavity</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Removal of the decayed portion of the tooth and placement of a dental filling</p></li><li><p>In more severe cases, a dental crown may be recommended</p></li></ul></li><li><p>Recommendation for improved oral hygiene routine and regular dental checkups</p></li></ul><p></p><p>Please note that the proposed treatment plan is subject to a thorough examination and may be adjusted based on the findings during the appointment. It is important to address these dental concerns to prevent further complications and maintain your oral health.</p><p></p><p>If you have any questions or concerns regarding the proposed treatment plan, please do not hesitate to contact our dental practice. We are here to provide you with the necessary information and support to make informed decisions about your dental care.</p><p></p><p>We look forward to seeing you at your next appointment to discuss the treatment plan in more detail and address any additional questions or concerns you may have.</p><p></p><p>Yours sincerely,</p>"
    patient_details = {
        "forename": "Harry",
        "surname": "Potter",
        "dob": "1905-01-01",
        "gender": "Male",
        "address": "4 Privat drive",
        "email": "harrypotter@gmail.com",
    }

    patients = []

    for i in range(0, 4):
        patients.append(
            create_new_patient(
                patient_details["forename"],
                patient_details["surname"],
                patient_details["dob"],
                patient_details["gender"],
                patient_details["address"],
                f"{i}" + patient_details["email"],
            )
        )
    for _i in range(0, 4):
        create_new_letter(user_id, consent_letter, patients[_i]["_id"], practice_id, 3000, 4000, 0.15, "gpt-4-turbo-preview")

    return token, practice_id


def test_successful_profile_get(insert_treatment_plan):
    token, practice_id = insert_treatment_plan
    response = client.get(
        "/profile/",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["name"] == "John Terry"
    assert data["user"]["email"] == "johnterry@gmail.com"


def test_profile_when_user_is_none(insert_treatment_plan):
    token, practice_id = insert_treatment_plan
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


def test_get_overview(insert_treatment_plan):
    token, practice_id = insert_treatment_plan
    response = client.get(
        "/profile/overview",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["letters"]) == 3
    assert len(data["triage_requests"]) == 0


def test_get_settings(insert_treatment_plan):
    token, practice_id = insert_treatment_plan
    response = client.get(
        "/profile/settings",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["name"] == "John Terry"
    assert data["user"]["email"] == "johnterry@gmail.com"
    assert len(data["practice_members"]) == 1


def test_register_member(insert_treatment_plan):
    token, practice_id = insert_treatment_plan

    response = client.post(
        "/profile/register",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "name": "Spongebob Squarepants",
            "email": "spongeebob@gmail.com",
            "password": "gary123",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["message"] == "Registered successfully"
    assert data["new_user"]["name"] == "Spongebob Squarepants"
    assert data["new_user"]["email"] == "spongeebob@gmail.com"
    assert data["new_user"]["practice_id"] == practice_id


def test_delete_member(insert_treatment_plan):
    token, practice_id = insert_treatment_plan
    practice_id = create_new_practice(
        "Willows Dental",
        "willows@dental.com",
        "https://www.willowsdental.com",
        "1 Prestatyn",
        "07880788392",
        gratis_password="YOUSHALLPASS!",
    )
    new_user = create_new_user("Spongebob Squarepants", "spongeebob@gmail.com", "gary123", practice_id, "Member")

    response = client.post(
        "/profile/delete",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "member_id": new_user["_id"],
            "practice_id": new_user["practice_id"],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["message"] == "Member deleted successfully"
