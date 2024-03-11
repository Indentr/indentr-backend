import json

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.database.crud import create_new_letter, create_new_patient
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


@pytest.fixture
def insert_consent_letter(register_and_login):
    token, user_id, practice_id = register_and_login
    # letter_id = "64dceaf941371bcccfaa5978"
    consent_letter = "<p>4 Privat Drive,<br>Little Whinging,<br>Surrey,<br>CR3 OBD</p><p></p><p>Dear Harry Potter,</p><p></p><p>Further to your recent appointment at which we discussed your treatment options, I have reviewed your symptoms and would like to propose a treatment plan for your dental concerns.</p><p></p><p>Based on your symptoms, it appears that you are experiencing toothache and have noticed some dark spots on one of your teeth during a routine checkup. After considering your responses to the questions, I recommend the following treatment plan:</p><p></p><p>Treatment for Toothache:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to evaluate the extent of the problem</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Root canal treatment if the tooth can be saved</p></li><li><p>Extraction of the tooth if it cannot be saved</p></li></ul></li><li><p>Prescription of pain relief medication, if necessary</p></li></ul><p></p><p>Treatment for Cavity:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to determine the extent of the cavity</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Removal of the decayed portion of the tooth and placement of a dental filling</p></li><li><p>In more severe cases, a dental crown may be recommended</p></li></ul></li><li><p>Recommendation for improved oral hygiene routine and regular dental checkups</p></li></ul><p></p><p>Please note that the proposed treatment plan is subject to a thorough examination and may be adjusted based on the findings during the appointment. It is important to address these dental concerns to prevent further complications and maintain your oral health.</p><p></p><p>If you have any questions or concerns regarding the proposed treatment plan, please do not hesitate to contact our dental practice. We are here to provide you with the necessary information and support to make informed decisions about your dental care.</p><p></p><p>We look forward to seeing you at your next appointment to discuss the treatment plan in more detail and address any additional questions or concerns you may have.</p><p></p><p>Yours sincerely,</p>"
    patient_details = {
        "forename": "Harry",
        "surname": "Potter",
        "dob": "1905-01-01",
        "gender": "Male",
        "address": "4 Privat drive",
        "email": "harrypotter@gmail.com",
    }

    patient = create_new_patient(
        patient_details["forename"],
        patient_details["surname"],
        patient_details["dob"],
        patient_details["gender"],
        patient_details["address"],
        patient_details["email"],
    )

    letter_id = create_new_letter(user_id, consent_letter, patient["_id"], practice_id, 3000, 4000, 0.15, "gpt-4-turbo-preview")
    return token, letter_id, consent_letter, patient_details, user_id, practice_id


def test_get_all_user_letters(insert_consent_letter):
    token, letter_id, consent_letter, patient_details, user_id, practice_id = insert_consent_letter
    response = client.post(
        "/files/get-files/",
        json={"file_type": "letter"},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["files"]) == 1


def test_get_consent_letter(insert_consent_letter):
    token, letter_id, consent_letter, patient_details, user_id, practice_id = insert_consent_letter
    file_type = "letter"
    response = client.get(
        f"/files/{file_type}/{letter_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["file"]["_id"] == letter_id
    assert data["file"]["consent_letter"] == consent_letter


def test_get_nonexistent_consent_letter(insert_consent_letter):
    token, letter_id, consent_letter, patient_details, user_id, practice_id = insert_consent_letter
    non_existent_id = ObjectId()  # generates random objectId
    file_type = "letter"
    response = client.get(
        f"/files/{file_type}/{str(non_existent_id)}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 400, response.text
    data = response.json()
    assert data["detail"] == "No letter found"


def test_save_consent_letter(insert_consent_letter):
    token, letter_id, consent_letter, patient_details, user_id, practice_id = insert_consent_letter
    consent_letter_document_template = {
        "_id": str(ObjectId(letter_id)),
        "consent_letter": "<p>4 Privat Drive,<br>Little Whinging,<br>Surrey,<br>CR3 OBD</p><p></p><p>Dear Harry Potter,</p><p></p><p>Further to your recent appointment at which we discussed your treatment options, I have reviewed your symptoms and would like to propose a treatment plan for your dental concerns.</p><p></p><p>Based on your symptoms, it appears that you are experiencing toothache and have noticed some dark spots on one of your teeth during a routine checkup. After considering your responses to the questions, I recommend the following treatment plan:</p><p></p><p>Treatment for Toothache:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to evaluate the extent of the problem</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Root canal treatment if the tooth can be saved</p></li><li><p>Extraction of the tooth if it cannot be saved</p></li></ul></li><li><p>Prescription of pain relief medication, if necessary</p></li></ul><p></p><p>Treatment for Cavity:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to determine the extent of the cavity</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Removal of the decayed portion of the tooth and placement of a dental filling</p></li><li><p>In more severe cases, a dental crown may be recommended</p></li></ul></li><li><p>Recommendation for improved oral hygiene routine and regular dental checkups</p></li></ul><p></p><p>Please note that the proposed treatment plan is subject to a thorough examination and may be adjusted based on the findings during the appointment. It is important to address these dental concerns to prevent further complications and maintain your oral health.</p><p></p><p>If you have any questions or concerns regarding the proposed treatment plan, please do not hesitate to contact our dental practice. We are here to provide you with the necessary information and support to make informed decisions about your dental care.</p><p></p><p>We look forward to seeing you at your next appointment to discuss the treatment plan in more detail and address any additional questions or concerns you may have.</p><p></p><p>Yours sincerely,</p>",
        "patient_info": {"forename": "Harry", "surname": "Potter", "dob": "1905-02-01", "gender": "Male", "address": "4 Privat drive"},
        "user_id": str(ObjectId(user_id)),
    }

    response = client.post(
        "/files/save-file/",
        json={"file_text": json.dumps(consent_letter_document_template["consent_letter"]), "file_id": letter_id, "file_type": "letter"},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["message"] == "File updated successfully"


def test_save_nonexistent_consent_letter(insert_consent_letter):
    token, letter_id, consent_letter, patient_details, user_id, practice_id = insert_consent_letter
    random_letter_id = ObjectId()
    consent_letter_document_template = {
        "_id": str(random_letter_id),  # left empty as this will make up random objectId
        "consent_letter": "<p>4 Privat Drive,<br>Little Whinging,<br>Surrey,<br>CR3 OBD</p><p></p><p>Dear Harry Potter,</p><p></p><p>Further to your recent appointment at which we discussed your treatment options, I have reviewed your symptoms and would like to propose a treatment plan for your dental concerns.</p><p></p><p>Based on your symptoms, it appears that you are experiencing toothache and have noticed some dark spots on one of your teeth during a routine checkup. After considering your responses to the questions, I recommend the following treatment plan:</p><p></p><p>Treatment for Toothache:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to evaluate the extent of the problem</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Root canal treatment if the tooth can be saved</p></li><li><p>Extraction of the tooth if it cannot be saved</p></li></ul></li><li><p>Prescription of pain relief medication, if necessary</p></li></ul><p></p><p>Treatment for Cavity:</p><ul><li><p>Examination and assessment of the affected tooth</p></li><li><p>X-rays to determine the extent of the cavity</p></li><li><p>Possible treatment options may include:</p><ul><li><p>Removal of the decayed portion of the tooth and placement of a dental filling</p></li><li><p>In more severe cases, a dental crown may be recommended</p></li></ul></li><li><p>Recommendation for improved oral hygiene routine and regular dental checkups</p></li></ul><p></p><p>Please note that the proposed treatment plan is subject to a thorough examination and may be adjusted based on the findings during the appointment. It is important to address these dental concerns to prevent further complications and maintain your oral health.</p><p></p><p>If you have any questions or concerns regarding the proposed treatment plan, please do not hesitate to contact our dental practice. We are here to provide you with the necessary information and support to make informed decisions about your dental care.</p><p></p><p>We look forward to seeing you at your next appointment to discuss the treatment plan in more detail and address any additional questions or concerns you may have.</p><p></p><p>Yours sincerely,</p>",
        "patient_info": {"forename": "Harry", "surname": "Potter", "dob": "1905-02-01", "gender": "Male", "address": "4 Privat drive"},
        "user_id": str(ObjectId(user_id)),
    }
    response = client.post(
        "/files/save-file/",
        json={"file_text": json.dumps(consent_letter_document_template["consent_letter"]), "file_id": str(random_letter_id), "file_type": "letter"},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 404, response.text
    data = response.json()
    assert data["detail"] == "No letter found"
