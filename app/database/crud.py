from typing import List, Optional

from fastapi import HTTPException
from mongoengine import DoesNotExist
from werkzeug.security import generate_password_hash

from app.database.schemas.config import Config
from app.database.schemas.letter import Letter
from app.database.schemas.patient import Patient
from app.database.schemas.practice import Practice
from app.database.schemas.pricing import Pricing
from app.database.schemas.triage import Triage
from app.database.schemas.user import User


# Practice ------------------------
def create_new_practice(practice_name: str, email: str, url: str, address: str, phone: str):
    # Create a Practice document
    new_practice = Practice(practice_name=practice_name, primary_email=email, website_url=url, address=address, phone=phone)
    new_practice.save()

    practice_dict = new_practice.to_mongo().to_dict()

    # Convert ObjectId to string in practice_dict
    practice_dict["_id"] = str(new_practice.id)

    return practice_dict["_id"]


def retrieve_practice_by_id(practice_id: str):
    try:
        practice = Practice.objects.get(id=practice_id)
        practice_dict = practice.to_mongo().to_dict()

        practice_dict["_id"] = str(practice.id)

        return practice_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Practice not found") from None


# User ---------------------------
def create_new_user(name: str, email: str, password: str, practice_id: str, role: str):
    # Check if provided role is valid
    if role not in User.ROLES:
        raise ValueError(f"Invalid role: {role}")

    # Hash the password
    hash_pass = generate_password_hash(password, method="scrypt")
    # Create a User document
    new_user = User(name=name, email=email, password=hash_pass, practice_id=practice_id, role=role)
    new_user.save()

    user_dict = new_user.to_mongo().to_dict()

    # Convert ObjectId to string in user_object
    user_dict["_id"] = str(new_user.id)
    practice_id = user_dict.get("practice_id")
    if practice_id:
        user_dict["practice_id"] = str(new_user.practice_id.id)
    user_dict.pop("password", None)

    return user_dict


def delete_member(member_id: str, practice_id: str):
    # Check that the user's practice_id matches the practice_id being passed and the role is Member
    user_to_delete = User.objects(id=member_id, practice_id=practice_id, role="Member").first()

    if not user_to_delete:
        raise HTTPException(status_code=404, detail="No member with that id found in practice")

    # Delete the user document
    user_to_delete.delete()


def retrieve_allow_user_registrations():
    # Check if user registrations are allowed
    configs_doc = Config.objects.first()
    if not configs_doc:
        raise HTTPException(status_code=404, detail="Config document not found.")

    return configs_doc.allow_registrations


def retrieve_user_by_id(user_id: str):
    try:
        user = User.objects.get(id=user_id)
        user_dict = user.to_mongo().to_dict()

        # Convert ObjectId to string in user_object
        user_dict["_id"] = str(user.id)
        practice_id = user_dict.get("practice_id")
        if practice_id:
            user_dict["practice_id"] = str(user.practice_id.id)
        user_dict.pop("password", None)

        return user_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


# Function to find a user by email
def retrieve_user_by_email(email: str):
    user = User.objects(email=email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user.to_mongo().to_dict()


def retrieve_all_practice_members(practice_id: str):
    # Query all users with the given practice_id
    practice_members = User.objects(practice_id=practice_id, role="Member")

    if not practice_members:
        return []

    # Convert the QuerySet to a list of dictionaries
    members_dict_list = []
    for member in practice_members:
        member_dict = member.to_mongo().to_dict()
        member_dict["_id"] = str(member.id)
        member_dict["practice_id"] = str(member.practice_id.id)
        member_dict.pop("password", None)
        members_dict_list.append(member_dict)

    return members_dict_list


# takes in a practice_id in order to search for all users with the same practice_id
def retrieve_practice_users_token_consumption(practice_id: str):
    practice_users_token_consumption = User.objects(practice_id=practice_id).only("name", "tokens_consumed")

    users_tokens_dict_list = []
    for user in practice_users_token_consumption:
        user_dict = user.to_mongo().to_dict()
        user_dict["_id"] = str(user.id)
        users_tokens_dict_list.append(user_dict)

    return users_tokens_dict_list


def update_user_details(user_id: str, email: str):
    try:
        user = User.objects.get(id=user_id)
        user.email = email
        user.save()

        user_dict = user.to_mongo().to_dict()

        # Convert ObjectId to string in user_object
        user_dict["_id"] = str(user_dict["_id"])
        user_dict.pop("password", None)

        return user_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


def update_user_tokens(user_id: str, tokens: int):
    try:
        user = User.objects.get(id=user_id)
        user.tokens_consumed += tokens
        user.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


# Patient ----------------------------
def create_new_patient(forename: str, surname: str, dob: str, gender: str, address: str, email: str, practice_id: Optional[str] = None):
    # Create a new instance of the Patient document with the provided patient details
    new_patient = Patient(forename=forename, surname=surname, dob=dob, gender=gender, address=address, email=email, practice_id=practice_id)

    # Save the new patient instance to the database
    new_patient.save()

    patient_dict = new_patient.to_mongo().to_dict()
    patient_dict["_id"] = str(patient_dict["_id"])
    if "practice_id" in patient_dict:
        patient_dict["practice_id"] = str(patient_dict["practice_id"])

    return patient_dict


def retrieve_patient_by_email(email: str):
    try:
        # Retrieve the patient document based on email
        patient = Patient.objects.get(email=email)
        patient_dict = patient.to_mongo().to_dict()
        if "practice_id" in patient_dict:
            patient_dict["practice_id"] = str(patient_dict["practice_id"])

        return patient_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Patient not found") from None


def retrieve_patients_by_ids(ids: List[str]):
    patients = []
    for patient_id in ids:
        try:
            # Retrieve the patient document based on patient_id
            patient = Patient.objects.get(id=patient_id)
            patient_dict = patient.to_mongo().to_dict()
            patient_dict["_id"] = str(patient_dict["_id"])
            if "practice_id" in patient_dict:
                patient_dict["practice_id"] = str(patient_dict["practice_id"])

            patients.append(patient_dict)

        except DoesNotExist:
            # Handle the case when a patient with the given patient_id is not found
            pass

    return patients


# Pricing ---------------------------
def retrieve_pricing(user_id: str):
    try:
        user = User.objects.get(id=user_id)
        pricing = Pricing.objects(practice_id=user.practice_id).first()

        if pricing is None:
            # raise HTTPException(status_code=404, detail="No pricing found")
            return "No pricing available, use best judgement"

        return pricing.treatment

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


# Letter ---------------------------
def create_new_letter(user_id: str, treatment_plan: str, patient_id: str, tokens_consumed: Optional[int] = None):
    try:
        # user = User.objects.get(id=user_id)

        # Create a new Letter document
        letter = Letter(consent_letter=treatment_plan, patient_id=patient_id, user_id=user_id, tokens_consumed=tokens_consumed)

        # Save the new letter to the database
        letter.save()

        return str(letter.id)

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


def retrieve_last_three_letters(user_id: str):
    try:
        letters = Letter.objects(user_id=user_id).order_by("-_id").limit(3)
        letters_list = []

    except DoesNotExist:
        # Handle the case where no letters are found
        return []

    for letter in letters:
        created_at = letter.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        letter_dict = letter.to_mongo().to_dict()
        letter_dict["createdAt"] = created_at
        letter_dict["_id"] = str(letter.id)
        letter_dict["user_id"] = str(letter.user_id.id)
        letter_dict["patient_id"] = str(letter.patient_id.id)

        letters_list.append(letter_dict)

    return letters_list


def retrieve_all_users_letters(user_id: str):
    try:
        # Query letters using MongoEngine
        letters = Letter.objects(user_id=user_id).order_by("-createdAt")

    except DoesNotExist as e:
        # Check if the exception is related to User or Letter
        if "User" in str(e):
            raise HTTPException(status_code=404, detail="User not found") from None
        elif "Letter" in str(e):
            raise HTTPException(status_code=404, detail="No letter found") from None
        else:
            raise e

    # Transform the MongoEngine documents to a list of dictionaries
    letters_list = []
    print("letters: ", letters)
    for letter in letters:
        created_at = letter.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        letter_dict = letter.to_mongo().to_dict()
        letter_dict["createdAt"] = created_at
        letter_dict["_id"] = str(letter_dict["_id"])
        letter_dict["user_id"] = str(letter_dict["user_id"])
        letter_dict["patient_id"] = str(letter_dict["patient_id"])
        letters_list.append(letter_dict)

    return letters_list


# Function to get a specific letter
def retrieve_user_letter(letter_id, user_id):
    # Query the letter using MongoEngine
    letter = Letter.objects(id=letter_id, user_id=user_id).first()

    if not letter:
        # Handle case where the letter doesn't exist or doesn't belong to the user
        raise HTTPException(status_code=400, detail="No letter found")

    created_at = letter.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
    letter_dict = letter.to_mongo().to_dict()
    letter_dict["createdAt"] = created_at
    letter_dict["_id"] = str(letter.id)
    letter_dict["user_id"] = str(letter.user_id.id)
    letter_dict["patient_id"] = str(letter.patient_id.id)

    return letter_dict


# Function to update the consent letter
def update_letter(letter_id, treatment_plan, user_id: str):
    # Use MongoEngine to find and update the document
    letter = Letter.objects(id=letter_id, user_id=user_id).first()

    if not letter:
        raise HTTPException(status_code=404, detail="No letter found")

    # Update the consent_letter field
    letter.consent_letter = treatment_plan
    letter.save()


# Triage ---------------------------
def create_triage_request(practice_id: str, email: str, diagnosis: str, overview: str, severity: str):
    # Try to find the patient by email within the practice
    try:
        patient = Patient.objects.get(email=email, practice_id=practice_id)
    except Patient.DoesNotExist:
        # Create a new triage request for new patient
        try:
            patient = Patient.objects.get(email=email)
        except Patient.DoesNotExist as err:
            raise HTTPException(status_code=404, detail="No patient exists with that email") from err

    # Create a new triage request document for existing patient
    new_triage = Triage(practice_id=practice_id, patient_id=patient, diagnosis=diagnosis, general_overview=overview, severity=severity)

    new_triage.save()


def retrieve_last_three_triage_requests(user_id: str):
    try:
        # Retrieve the user document to get the associated practice_id
        user = User.objects.get(id=user_id)
        practice_id = user.practice_id

        triage_requests = Triage.objects(practice_id=practice_id).order_by("-_id").limit(3)

        # Transform the MongoEngine documents to a list of dictionaries
        triage_list = []
        for triage in triage_requests:
            triage_dict = triage.to_mongo().to_dict()
            triage_dict["_id"] = str(triage.id)
            triage_dict["practice_id"] = str(triage.practice_id.id)
            if "patient_id" in triage_dict:
                triage_dict["patient_id"] = str(triage_dict["patient_id"])
            triage_list.append(triage_dict)

        return triage_list

    except DoesNotExist:
        # Handle the case where no letters are found
        return []
