import base64
import json
from datetime import datetime
from io import BytesIO
from string import ascii_lowercase
from typing import Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException
from mongoengine import DoesNotExist, NotUniqueError
from werkzeug.security import generate_password_hash

from app.database.schemas.audio_note import AudioNote
from app.database.schemas.config import Config
from app.database.schemas.example_consent_letters import VectorExampleLetter
from app.database.schemas.letter import Letter
from app.database.schemas.letter_config import LetterConfig
from app.database.schemas.patient import Patient, PatientName
from app.database.schemas.practice import Practice
from app.database.schemas.pricing import Pricing
from app.database.schemas.prompt import Prompt
from app.database.schemas.triage import Triage
from app.database.schemas.user import User


# GPT Prompts ------------------------
def create_new_prompt(title: str, prompt_text: str):
    # Create a Prompt document
    new_prompt = Prompt(title=title, prompt_text=prompt_text)
    new_prompt.save()


def retrieve_prompt_by_title(title: str):
    try:
        prompt = Prompt.objects.get(title=title)
        return prompt.prompt_text

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Prompt not found") from None


# Practice ------------------------
def create_new_practice(practice_name: str, email: str, url: str, address: str, phone: str, triage_email: str = None):
    # Default triage email destination to practice email if it is unset
    if not triage_email:
        triage_email = email

    # Create a Practice document
    new_practice = Practice(
        practice_name=practice_name, primary_email=email, website_url=url, address=address, phone=phone, triage_email=triage_email
    )
    new_practice.save()

    practice_dict = new_practice.to_mongo().to_dict()

    # Convert ObjectId to string in practice_dict
    practice_dict["_id"] = str(new_practice.id)

    return practice_dict["_id"]


# Function to find a practice by email
def retrieve_practice_by_email(email: str):
    practice = Practice.objects(primary_email=email).first()

    if not practice:
        raise HTTPException(status_code=404, detail="Practice not found")

    return practice.to_mongo().to_dict()


def retrieve_practice_by_id(practice_id: str):
    try:
        practice = Practice.objects.get(id=practice_id)
        practice_dict = practice.to_mongo().to_dict()

        practice_dict["_id"] = str(practice.id)

        return practice_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Practice not found") from None


def update_practice_details(practice_id: str, name: str = None, email: str = None, address: str = None, website: str = None):
    try:
        practice = Practice.objects.get(id=practice_id)
        if name:
            practice.practice_name = name

        if email:
            try:
                # Attempt to retrieve the user by email
                existing_practice = retrieve_practice_by_email(email)
            except HTTPException as e:
                # Handle the 404 exception if user is not found
                if e.status_code == 404:
                    existing_practice = None
                else:
                    raise

            # Check if the email already exists
            if existing_practice:
                raise HTTPException(status_code=400, detail="Email already in use")

            practice.primary_email = email

        if address:
            practice.address = address

        if website:
            practice.website_url = website

        practice.save()

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



def retrieve_all_practice_users(practice_id: str):
    # Query all users with the given practice_id
    practice_members = User.objects(practice_id=practice_id).only("name", "email", "role").select_related()

    if not practice_members:
        return []

    # Convert the QuerySet to a list of dictionaries
    members_dict_list = []
    for member in practice_members:
        member_dict = member.to_mongo().to_dict()
        member_dict["_id"] = str(member.id)
        members_dict_list.append(member_dict)

    return members_dict_list


def update_user_details(user_id: str, name: str = None, email: str = None, password: str = None):
    try:
        user = User.objects.get(id=user_id)
        if name:
            user.name = name

        if email:
            try:
                # Attempt to retrieve the user by email
                existing_user = retrieve_user_by_email(email)
            except HTTPException as e:
                # Handle the 404 exception if user is not found
                if e.status_code == 404:
                    existing_user = None
                else:
                    raise

            # Check if the email already exists
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already in use")

            user.email = email

        if password:
            hash_pass = generate_password_hash(password, method="scrypt")
            user.password = hash_pass

        user.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


# Patient ----------------------------
def create_new_patient(forename: str, surname: str, dob: str, gender: str, address: str, email: str, practice_id: Optional[str] = None):
    try:
        # Check if a patient with the same email already exists
        existing_patient = Patient.objects(email=email).first()
        if existing_patient:
            raise HTTPException(status_code=400, detail="Patient with this email already exists")

        # Create a new instance of the Patient document with the provided patient details
        new_patient = Patient(
            forename=forename.capitalize(),
            surname=surname.capitalize(),
            dob=dob,
            gender=gender,
            address=address,
            email=email,
            practice_id=practice_id,
        )

        # Save the new patient instance to the database
        new_patient.save()

        patient_dict = new_patient.to_mongo().to_dict()
        patient_dict["_id"] = str(patient_dict["_id"])
        if "practice_id" in patient_dict:
            patient_dict["practice_id"] = str(patient_dict["practice_id"])

        return patient_dict

    except NotUniqueError:
        # Handle the case where a patient with the same email already exists
        raise HTTPException(status_code=400, detail="Patient with this email already exists") from None


def delete_patient(practice_id: str, patient_id: str):
    patient_to_delete = Patient.objects(id=patient_id, practice_id=practice_id).first()

    if not patient_to_delete:
        raise HTTPException(status_code=404, detail="No patient with that id found in practice")

    # Delete the patient document
    patient_to_delete.delete()
    Triage.objects(patient_id=patient_id).delete()
    Letter.objects(patient_id=patient_id).delete()
    AudioNote.objects(patient_id=patient_id).delete()


def retrieve_all_patients_by_practice(practice_id: str):
    try:
        patients = (
            Patient.objects(practice_id=practice_id)
            .only("forename", "surname", "gender", "email", "dob", "address")
            .order_by("forename")
            .select_related()
        )

        patients_list = []
        for patient in patients:
            patient_dict = patient.to_mongo().to_dict()
            patient_dict["_id"] = str(patient_dict["_id"])
            patients_list.append(patient_dict)

        return patients_list

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="No patients found in practice") from None


def retrieve_patients_alphabet_status(practice_id: str):
    try:
        pipeline = [
            {"$match": {"practice_id": ObjectId(practice_id)}},
            {"$group": {"_id": {"$substr": ["$forename", 0, 1]}, "count": {"$sum": 1}}},
        ]

        result = Patient.objects.aggregate(*pipeline)

        # Create a dictionary with default value 0 for all letters
        alphabet_status = {letter: 0 for letter in ascii_lowercase}

        # Update the dictionary based on the aggregation result
        for entry in result:
            first_letter = entry["_id"].lower()
            count = entry["count"]
            alphabet_status[first_letter] = count if count > 0 else 0

        return alphabet_status

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Error retrieving alphabet_status") from None


def retrieve_all_practices_patients_filtered_by_char(practice_id: str, starts_with: str):
    try:
        pipeline = [
            {"$match": {"practice_id": ObjectId(practice_id), "forename": {"$regex": f"^{starts_with}", "$options": "i"}}},
            {"$sort": {"forename": 1}},
            {"$project": {"practice_id": 0}},
        ]

        patients = Patient.objects.aggregate(*pipeline)

        result = [
            {
                "_id": str(doc["_id"]),
                "forename": doc["forename"],
                "surname": doc["surname"],
                "email": doc["email"],
                "gender": doc["gender"],
                "dob": doc["dob"],
                "address": doc["address"],
            }
            for doc in patients
        ]

        return result

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="No patients found") from None


def retrieve_patient_by_email(email: str, practice_id: str = None ):
    try:
        # Retrieve the patient document based on email
        if(practice_id != None):
            patient = Patient.objects.get(email=email, practice_id=practice_id)
        else:
            patient = Patient.objects.get(email=email)

        patient_dict = patient.to_mongo().to_dict()
        if "practice_id" in patient_dict:
            patient_dict["practice_id"] = str(patient_dict["practice_id"])

        return patient_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Patient not found") from None


# Function to check if a patient exists
def retrieve_patient_exists_by_email_and_practice(email: str, practice_id: str) -> bool:
    try:
        # Attempt to retrieve the patient by email and practice_id
        Patient.objects.get(email=email, practice_id=practice_id)
        # If the function successfully retrieves a patient, return True
        return True
    except DoesNotExist:
        # If a DoesNotExist exception is caught, it means no patient was found with the given criteria, so return False
        return False


def retrieve_patient_by_id(patient_id: str, practice_id):
    try:
        # Retrieve the patient document based on patient_id
        patient = Patient.objects.get(id=patient_id, practice_id=practice_id)
        patient_dict = patient.to_mongo().to_dict()
        patient_dict["_id"] = str(patient_dict["_id"])
        if "practice_id" in patient_dict:
            patient_dict["practice_id"] = str(patient_dict["practice_id"])

        return patient_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Patient not found") from None


def update_patients_practice_id(patient_id: str, practice_id: str):
    try:
        patient = Patient.objects.get(id=patient_id)
        patient.practice_id = ObjectId(practice_id)
        patient.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Patient not found") from None


# Pricing ---------------------------
def retrieve_pricing(practice_id: str):
    try:
        pricing = Pricing.objects(practice_id=practice_id).only("treatment", "price")

        if pricing is None:
            return None

        pricing_list = []
        for price in pricing:
            price_dict = price.to_mongo().to_dict()
            del price_dict["_id"]
            pricing_list.append(price_dict)

        return pricing_list

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


# Letter ---------------------------
def create_new_letter(
    user_id: str, text: str, patient_id: str, input_tokens: int = None, output_tokens: int = None, cost: int = None, model: str = None
):
    try:
        # Fetch the patient object
        patient = Patient.objects.get(id=patient_id)

        patient_details = PatientName(forename=patient.forename, surname=patient.surname)

        # Create a new Letter document
        letter = Letter(
            consent_letter=text,
            patient_id=patient_id,
            user_id=user_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            model=model,
            patient_details=patient_details,
        )

        # Save the new letter to the database
        letter.save()

        return str(letter.id)

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found") from None


def delete_letter(user_id: str, file_id: str):
    letter_to_delete = Letter.objects(id=file_id, user_id=user_id).first()

    if not letter_to_delete:
        raise HTTPException(status_code=404, detail="No member with that id found in practice")

    # Delete the user document
    letter_to_delete.delete()


def retrieve_last_three_letters(user_id: str):
    try:
        letters = Letter.objects(user_id=user_id).only("consent_letter", "patient_id", "createdAt").order_by("-_id").limit(3)

        letters_list = []

    except DoesNotExist:
        # Handle the case where no letters are found
        return []

    for letter in letters:
        created_at = letter.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        letter_dict = letter.to_mongo().to_dict()
        letter_dict["createdAt"] = created_at
        letter_dict["_id"] = str(letter.id)
        patient_details = letter.patient_id.to_mongo().to_dict()
        del patient_details["_id"]
        if "practice_id" in patient_details:
            del patient_details["practice_id"]
        letter_dict["patient_details"] = patient_details
        del letter_dict["patient_id"]

        letters_list.append(letter_dict)

    return letters_list


def retrieve_patients_last_three_letters(patient_id: str):
    try:
        letters = Letter.objects(patient_id=patient_id).only("consent_letter", "patient_id", "createdAt").order_by("-_id").limit(3)
        letters_list = []

    except DoesNotExist:
        # Handle the case where no letters are found
        return []

    for letter in letters:
        created_at = letter.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        letter_dict = letter.to_mongo().to_dict()
        letter_dict["createdAt"] = created_at
        letter_dict["_id"] = str(letter.id)
        patient_details = letter.patient_id.to_mongo().to_dict()
        del patient_details["_id"]
        if "practice_id" in patient_details:
            del patient_details["practice_id"]
        del patient_details["dob"]
        del patient_details["gender"]
        del patient_details["address"]
        del patient_details["email"]
        letter_dict["patient_details"] = patient_details
        del letter_dict["patient_id"]

        letters_list.append(letter_dict)

    return letters_list


def retrieve_all_users_letters(user_id: str):
    try:
        letters = Letter.objects(user_id=user_id).only("consent_letter", "patient_id", "createdAt").order_by("-createdAt").select_related()

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
    for letter in letters:
        created_at = letter.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        letter_dict = letter.to_mongo().to_dict()
        letter_dict["createdAt"] = created_at
        letter_dict["_id"] = str(letter_dict["_id"])
        patient_details = letter.patient_id.to_mongo().to_dict()
        del patient_details["_id"]
        if "practice_id" in patient_details:
            del patient_details["practice_id"]
        letter_dict["patient_details"] = patient_details
        del letter_dict["patient_id"]

        letters_list.append(letter_dict)

    return letters_list


def retrieve_all_users_letters_filtered_by_char(user_id: str, starts_with: str):
    try:
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
            {"$unwind": "$patient"},
            {"$match": {"patient.forename": {"$regex": f"^{starts_with}", "$options": "i"}}},
            {"$sort": {"createdAt": -1}},
        ]

        letters = Letter.objects.aggregate(*pipeline)

        result = [
            {
                "_id": str(doc["_id"]),
                "consent_letter": doc["consent_letter"],
                "patient_details": {
                    "forename": doc["patient"]["forename"],
                    "surname": doc["patient"]["surname"],
                },
                "createdAt": doc["createdAt"],
            }
            for doc in letters
        ]

        return result

    except DoesNotExist as e:
        if "Letter" in str(e):
            raise HTTPException(status_code=404, detail="No letter found") from None
        else:
            raise e


def retrieve_letters_alphabet_status(user_id: str):
    try:
        # Use the aggregation framework to calculate alphabet status
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
            {"$unwind": "$patient"},
            {"$group": {"_id": {"$substr": ["$patient.forename", 0, 1]}, "count": {"$sum": 1}}},
        ]

        result = Letter.objects.aggregate(*pipeline)

        # Create a dictionary with default value 0 for all letters
        alphabet_status = {letter: 0 for letter in ascii_lowercase}

        # Update the dictionary based on the aggregation result
        for entry in result:
            first_letter = entry["_id"].lower()
            count = entry["count"]
            alphabet_status[first_letter] = count if count > 0 else 0

        return alphabet_status

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Error retrieving alphabet_status") from None


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
    if "tokens_consumed" in letter_dict:
        del letter_dict["tokens_consumed"]

    return letter_dict


# Function to update the consent letter
def update_letter(letter_id, text, user_id: str):
    # Use MongoEngine to find and update the document
    letter = Letter.objects(id=letter_id, user_id=user_id).first()

    if not letter:
        raise HTTPException(status_code=404, detail="No letter found")

    # Update the consent_letter field
    letter.consent_letter = text
    letter.save()


# Triage ---------------------------
def create_triage_request(
    practice_id: str,
    email: str,
    diagnosis: str,
    reason_for_request: str,
    overview: str = None,
    severity: str = None,
    requested_date: str = None,
    GPT_QA: str = None,
    instruction: bool = False
):
    # Try to find the patient by email within the practice
    try:
        patient = Patient.objects.get(email=email, practice_id=practice_id)
    except Patient.DoesNotExist:
        # if the patient doesn't exist within the practice
        # Check if the patient already exists within our system
        try:
            patient = Patient.objects.get(email=email)
        except Patient.DoesNotExist as err:
            raise HTTPException(status_code=404, detail="No patient exists with that email") from err

    if requested_date:
        requested_date = datetime.strptime(requested_date, "%Y-%m-%d")

    patient_details = PatientName(forename=patient.forename, surname=patient.surname)

    # Create a new triage request document for existing patient
    new_triage = Triage(
        practice_id=practice_id,
        patient_id=patient,
        diagnosis=diagnosis,
        general_overview=overview,
        severity=severity,
        requested_date=requested_date,
        GPT_QA=json.dumps(GPT_QA),
        patient_details=patient_details,
        instruction=instruction,
        reason_for_request=reason_for_request,
    )

    new_triage.save()


def delete_triage_requests(triage_requests: List[str], practice_id: str):
    try:
        # Delete the specified Triage objects
        Triage.objects(id__in=triage_requests, practice_id=practice_id).delete()

    except Exception as err:
        raise HTTPException(status_code=400, detail="Error deleting triage requests") from err


def retrieve_triage_request(triage_id: str, practice_id: str):
    triage = Triage.objects(id=triage_id, practice_id=practice_id).first()

    if not triage:
        raise HTTPException(status_code=404, detail="Triage request not found")

    # Update the 'opened' field to True
    triage.update(set__opened=True)

    triage_dict = triage.to_mongo().to_dict()
    triage_dict["_id"] = str(triage.id)
    triage_dict["practice_id"] = str(triage.practice_id.id)
    patient_details = triage.patient_id.to_mongo().to_dict()
    patient_details["_id"] = str(patient_details["_id"])
    if "practice_id" in patient_details:
        patient_details["practice_id"] = str(patient_details["practice_id"])
    triage_dict["patient_details"] = patient_details
    del triage_dict["patient_id"]

    return triage_dict


def retrieve_all_triage_requests(practice_id: str):
    try:
        triage_requests = (
            Triage.objects(practice_id=practice_id)
            .only("opened", "severity", "diagnosis", "patient_id", "practice_id", "folder", "created_at")
            .order_by("-_id")
            .select_related()
        )

        # Transform the MongoEngine documents to a list of dictionaries
        triage_list = []
        for triage in triage_requests:
            triage_dict = triage.to_mongo().to_dict()
            triage_dict["_id"] = str(triage.id)
            triage_dict["practice_id"] = str(triage.practice_id.id)
            patient_details = {"_id": str(triage.patient_id.id), "forename": triage.patient_id.forename, "surname": triage.patient_id.surname}
            triage_dict["patient_details"] = patient_details
            del triage_dict["patient_id"]

            triage_list.append(triage_dict)

        return triage_list

    except DoesNotExist:
        # Handle the case where no letters are found
        return []


def retrieve_all_triage_requests_by_folder(practice_id: str, folder: str):
    try:
        triage_requests = (
            Triage.objects(practice_id=practice_id, folder=folder)
            .only("opened", "severity", "diagnosis", "patient_id", "practice_id", "folder")
            .order_by("-_id")
            .select_related()
        )

        # Transform the MongoEngine documents to a list of dictionaries
        triage_list = []
        for triage in triage_requests:
            triage_dict = triage.to_mongo().to_dict()
            triage_dict["_id"] = str(triage.id)
            triage_dict["practice_id"] = str(triage.practice_id.id)
            patient_details = {"_id": str(triage.patient_id.id), "forename": triage.patient_id.forename, "surname": triage.patient_id.surname}
            triage_dict["patient_details"] = patient_details
            del triage_dict["patient_id"]

            triage_list.append(triage_dict)

        return triage_list

    except DoesNotExist:
        # Handle the case where no letters are found
        return []


def retrieve_last_three_triage_requests(user_id: str):
    try:
        # Retrieve the user document to get the associated practice_id
        user = User.objects.get(id=user_id)
        practice_id = user.practice_id

        triage_requests = (
            Triage.objects(practice_id=practice_id)
            .only("opened", "severity", "diagnosis", "patient_id", "practice_id", "folder", "created_at")
            .order_by("-_id")
            .limit(3)
            .select_related()
        )

        # Transform the MongoEngine documents to a list of dictionaries
        triage_list = []
        for triage in triage_requests:
            triage_dict = triage.to_mongo().to_dict()
            triage_dict["_id"] = str(triage.id)
            triage_dict["practice_id"] = str(triage.practice_id.id)
            patient_details = {"_id": str(triage.patient_id.id), "forename": triage.patient_id.forename, "surname": triage.patient_id.surname}
            triage_dict["patient_details"] = patient_details
            del triage_dict["patient_id"]

            triage_list.append(triage_dict)

        return triage_list

    except DoesNotExist:
        # Handle the case where no letters are found
        return []


def update_triage_requests_opened(triage_requests: List[str], opened: bool, practice_id: str):
    try:
        # Find and update the specified Triage objects in one go
        Triage.objects(id__in=triage_requests, practice_id=practice_id).update(set__opened=opened)

    except DoesNotExist as e:
        # Handle the case where a Triage object is not found
        raise HTTPException(status_code=404, detail=str(e)) from None


def update_triage_requests_folder(triage_requests: List[str], folder: str, practice_id: str):
    try:
        # Find and update the specified Triage objects in one go
        Triage.objects(id__in=triage_requests, practice_id=practice_id).update(set__folder=folder)

    except DoesNotExist as e:
        # Handle the case where a Triage object is not found
        raise HTTPException(status_code=404, detail=str(e)) from None


# Note ---------------------------
def create_audio_note(patient_id: str, user_id: str, practice_id: str, audio_bytesio: BytesIO, transcript: str, formatted_notes: str) -> str:
    try:
        # Convert BytesIO to bytes
        audio_bytes = audio_bytesio.getvalue()

        # Fetch the patient object
        patient = Patient.objects.get(id=patient_id)

        patient_details = PatientName(forename=patient.forename, surname=patient.surname)

        audio_note = AudioNote(
            patient_id=patient_id,
            user_id=user_id,
            practice_id=practice_id,
            audio=audio_bytes,
            transcript=transcript,
            formatted_notes=formatted_notes,
            patient_details=patient_details,
        )
        audio_note.save()

        # Return the ID of the created note
        return str(audio_note.id)  # or audio_note.pk for primary key

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


def delete_note(practice_id: str, file_id: str):
    note_to_delete = AudioNote.objects(id=file_id, practice_id=practice_id).first()

    if not note_to_delete:
        raise HTTPException(status_code=404, detail="No note with that id found in practice")

    # Delete the note document
    note_to_delete.delete()


def retrieve_all_users_notes(user_id: str):
    try:
        # Query letters using MongoEngine
        notes = AudioNote.objects(user_id=user_id).only("patient_id", "formatted_notes", "createdAt").order_by("-createdAt").select_related()

    except DoesNotExist as e:
        # Check if the exception is related to User or Letter
        if "User" in str(e):
            raise HTTPException(status_code=404, detail="User not found") from None
        elif "Letter" in str(e):
            raise HTTPException(status_code=404, detail="No letter found") from None
        else:
            raise e

    # Transform the MongoEngine documents to a list of dictionaries
    notes_list = []
    for note in notes:
        created_at = note.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        note_dict = note.to_mongo().to_dict()
        note_dict["createdAt"] = created_at
        note_dict["_id"] = str(note_dict["_id"])
        patient_details = note.patient_id.to_mongo().to_dict()
        del patient_details["_id"]
        if "practice_id" in patient_details:
            del patient_details["practice_id"]
        del patient_details["dob"]
        del patient_details["gender"]
        del patient_details["address"]
        del patient_details["email"]
        note_dict["patient_details"] = patient_details
        del note_dict["patient_id"]

        notes_list.append(note_dict)

    return notes_list


# Function to get a specific letter
def retrieve_note(note_id: str, user_id: str):
    # Query the letter using MongoEngine
    note = AudioNote.objects(id=note_id, user_id=user_id).only("patient_id", "formatted_notes", "createdAt").first()

    if not note:
        # Handle case where the letter doesn't exist or doesn't belong to the user
        raise HTTPException(status_code=400, detail="No letter found")

    created_at = note.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
    note_dict = note.to_mongo().to_dict()
    note_dict["createdAt"] = created_at
    note_dict["_id"] = str(note_dict["_id"])
    patient_details = note.patient_id.to_mongo().to_dict()
    del patient_details["_id"]
    if "practice_id" in patient_details:
        del patient_details["practice_id"]
    del patient_details["dob"]
    del patient_details["gender"]
    del patient_details["address"]
    note_dict["patient_details"] = patient_details
    del note_dict["patient_id"]

    return note_dict


def retrieve_notes_alphabet_status(user_id: str):
    try:
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
            {"$unwind": "$patient"},
            {"$group": {"_id": {"$substr": ["$patient.forename", 0, 1]}, "count": {"$sum": 1}}},
        ]

        result = AudioNote.objects.aggregate(*pipeline)

        # Create a dictionary with default value 0 for all letters
        alphabet_status = {letter: 0 for letter in ascii_lowercase}

        # Update the dictionary based on the aggregation result
        for entry in result:
            first_letter = entry["_id"].lower()
            count = entry["count"]
            alphabet_status[first_letter] = count if count > 0 else 0

        return alphabet_status

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Error retrieving alphabet_status") from None


def retrieve_all_users_notes_filtered_by_char(user_id: str, starts_with: str):
    try:
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
            {"$unwind": "$patient"},
            {"$match": {"patient.forename": {"$regex": f"^{starts_with}", "$options": "i"}}},
            {"$sort": {"createdAt": -1}},
            {"$project": {"audio": 0, "practice_id": 0, "user_id": 0, "transcript": 0}},
        ]

        notes = AudioNote.objects.aggregate(*pipeline)

        result = [
            {
                "_id": str(doc["_id"]),
                "formatted_notes": doc["formatted_notes"],
                "patient_details": {
                    "forename": doc["patient"]["forename"],
                    "surname": doc["patient"]["surname"],
                },
                "createdAt": doc["createdAt"],
            }
            for doc in notes
        ]

        return result

    except DoesNotExist as e:
        if "Letter" in str(e):
            raise HTTPException(status_code=404, detail="No letter found") from None
        else:
            raise e


def retrieve_patients_last_three_notes(patient_id: str):
    try:
        notes = AudioNote.objects(patient_id=patient_id).only("patient_id", "formatted_notes", "createdAt").order_by("-_id").limit(3).select_related()

    except DoesNotExist:
        # Handle the case where no letters are found
        return []

    notes_list = []
    for note in notes:
        created_at = note.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        note_dict = note.to_mongo().to_dict()
        note_dict["createdAt"] = created_at
        note_dict["_id"] = str(note_dict["_id"])
        patient_details = note.patient_id.to_mongo().to_dict()
        del patient_details["_id"]
        if "practice_id" in patient_details:
            del patient_details["practice_id"]
        del patient_details["dob"]
        del patient_details["gender"]
        del patient_details["address"]
        del patient_details["email"]
        note_dict["patient_details"] = patient_details
        del note_dict["patient_id"]

        notes_list.append(note_dict)

    return notes_list


# Function to update the consent letter
def update_note(note_id, text, user_id: str):
    # Use MongoEngine to find and update the document
    note = AudioNote.objects(id=note_id, user_id=user_id).first()

    if not note:
        raise HTTPException(status_code=404, detail="No note found")

    # Update the consent_letter field
    note.formatted_notes = text
    note.save()


def update_formatted_notes(note_id: str, new_formatted_notes: str):
    try:
        # Fetch the complete document
        audio_note = AudioNote.objects.get(id=note_id)

        if not audio_note:
            raise HTTPException(status_code=404, detail="No audio note found")

        audio_note.formatted_notes = new_formatted_notes

        # Save the updated document
        audio_note.save()

    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error") from None


# Vector example letters ---------------------------------
def create_new_vector_letter(consent_letter: str, title: str, plot_embedding: List[float]):
    try:
        letter = VectorExampleLetter(consent_letter=consent_letter, title=title, plot_embedding=plot_embedding)
        letter.save()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


def retrieve_vector_letters(pipeline):
    try:
        result = VectorExampleLetter.objects.aggregate(*pipeline)
        return list(result)

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Error retrieving alphabet_status") from None


# Pricing ---------------------------
def retrieve_price_list(practice_id: str):
    try:
        # Fetch pricing documents for the given practice_id
        pricing_docs = Pricing.objects(practice_id=practice_id).select_related()

        # If no documents are found, return an empty list instead of raising an exception
        if not pricing_docs:
            return []

        price_list = []
        for pricing in pricing_docs:
            pricing_dict = pricing.to_mongo().to_dict()
            pricing_dict["_id"] = str(pricing_dict["_id"])
            pricing_dict["practice_id"] = str(pricing_dict["practice_id"])
            price_list.append(pricing_dict)

        return price_list

    except Exception as e:
        # Handle any other exceptions that might occur
        raise HTTPException(status_code=500, detail=str(e)) from None


def update_price_list(price_list: List[Dict], practice_id: str):
    try:
        # Delete all existing records for this practice_id
        Pricing.objects(practice_id=practice_id).delete()

        if price_list:
            Pricing.objects.insert([Pricing(treatment=item["treatment"], price=item["price"], practice_id=practice_id) for item in price_list])

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Practice not found") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# Letter config ---------------------------------
def create_letter_config(practice_id: str):
    try:
        letter_config = LetterConfig(practice_id=practice_id)
        letter_config.save()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


def retrieve_letter_config(practice_id: str):
    try:
        # Fetch pricing documents for the given practice_id
        letter_config = LetterConfig.objects(practice_id=practice_id).first().select_related()

        if not letter_config:
            # Handle case where the letter doesn't exist or doesn't belong to the user
            raise HTTPException(status_code=400, detail="No letter config found")

        letter_config_dict = letter_config.to_mongo().to_dict()

        # Encode to base64 string before sending back
        if "image" in letter_config_dict:
            image_data = letter_config_dict["image"]
            letter_config_dict["image"] = base64.b64encode(image_data).decode("utf-8")

        del letter_config_dict["_id"]
        del letter_config_dict["practice_id"]

        return letter_config_dict

    except Exception as e:
        # Handle any other exceptions that might occur
        raise HTTPException(status_code=500, detail=str(e)) from None


def update_letter_image(practice_id: str, image_data: bytes):
    letter_config = LetterConfig.objects(practice_id=practice_id).first()

    if not letter_config:
        raise HTTPException(status_code=404, detail="LetterConfig not found for practice_id")

    letter_config.image = image_data
    letter_config.save()


def update_letter_config(
    practice_id: str,
    include_image: bool,
    patient_address: bool,
    date: bool,
    salutation: str,
    recipient_naming: str,
    pricing: bool,
    include_insurance_info: bool,
    patient_insurance_info: str,
    patient_signature: bool,
    dentist_signature: bool,
    practice_contact_details: bool,
    contact_details_text: str,
    sign_off: str,
    dentist_naming: str,
):
    try:
        letter_config = LetterConfig.objects.get(practice_id=practice_id)
        letter_config.include_image = include_image
        letter_config.patient_address = patient_address
        letter_config.date = date
        letter_config.salutation = salutation
        letter_config.recipient_naming = recipient_naming
        letter_config.pricing = pricing
        letter_config.include_insurance_info = include_insurance_info
        letter_config.patient_insurance_info = patient_insurance_info
        letter_config.patient_signature = patient_signature
        letter_config.dentist_signature = dentist_signature
        letter_config.practice_contact_details = practice_contact_details
        letter_config.contact_details_text = contact_details_text
        letter_config.sign_off = sign_off
        letter_config.dentist_naming = dentist_naming
        letter_config.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Letter config not found") from None
