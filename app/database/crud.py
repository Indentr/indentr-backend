import json
from datetime import datetime
from io import BytesIO
from string import ascii_lowercase
from typing import List, Optional

from bson import ObjectId
from fastapi import HTTPException
from mongoengine import DoesNotExist, NotUniqueError
from werkzeug.security import generate_password_hash

from app.database.schemas.audio_note import AudioNote
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


def delete_price_list_crud(practice_id: str):
    try:
        # Fetch pricing documents for the given practice_id
        pricing_docs = Pricing.objects(practice_id=practice_id)

        # Check if any documents were found
        if not pricing_docs:
            raise DoesNotExist

        # Delete all fetched documents
        pricing_docs.delete()
        return {"message": "Price list deleted successfully"}

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Price list not found for the given practice") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") from None


def delete_service_from_price_list(practice_id: str, service_name: str):
    try:
        # Fetch and delete the specific pricing document
        pricing_doc = Pricing.objects(practice_id=practice_id, treatment=service_name).first()
        if not pricing_doc:
            raise DoesNotExist

        pricing_doc.delete()
        return {"message": f"Treatment '{service_name}' deleted successfully"}

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Treatment not found for the specified practice") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") from None


def retrieve_price_list(practice_id: str):
    try:
        # Fetch pricing documents for the given practice_id
        pricing_docs = Pricing.objects(practice_id=practice_id)

        # Check if any documents were found
        if not pricing_docs:
            raise DoesNotExist

        # Convert documents to a list of dictionaries
        price_list = [doc.to_mongo().to_dict() for doc in pricing_docs]
        # Optionally, process the price_list to format it as required
        # for example, convert ObjectId to string, etc.
        return price_list

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Price list not found for the given practice") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}") from None


def update_price_list(price_list: str, practice_id: str):
    try:
        price_list_data = json.loads(price_list)
        service_list = [item["service"] for item in price_list_data]

        # Update existing documents or create new ones
        for item in price_list_data:
            pricing = Pricing.objects(treatment=item["service"], practice_id=practice_id).first()
            if pricing:
                pricing.price = item["price"]
                pricing.save()
            else:
                pricing = Pricing(treatment=item["service"], price=item["price"], practice_id=practice_id)
                pricing.save()

        # Delete records not in the updated price list
        Pricing.objects(practice_id=practice_id, treatment__nin=service_list).delete()

        # Retrieve and return the updated price list
        updated_prices = Pricing.objects(practice_id=practice_id)
        updated_prices_list = [price.to_mongo().to_dict() for price in updated_prices]
        return updated_prices_list

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Practice not found") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


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
    try:
        # Check if a patient with the same email already exists
        existing_patient = Patient.objects(email=email).first()
        if existing_patient:
            raise HTTPException(status_code=400, detail="Patient with this email already exists")

        # Create a new instance of the Patient document with the provided patient details
        new_patient = Patient(forename=forename, surname=surname, dob=dob, gender=gender, address=address, email=email, practice_id=practice_id)

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


def retrieve_patient_by_id(patient_id: str):
    try:
        # Retrieve the patient document based on patient_id
        patient = Patient.objects.get(id=patient_id)
        patient_dict = patient.to_mongo().to_dict()
        patient_dict["_id"] = str(patient_dict["_id"])
        if "practice_id" in patient_dict:
            patient_dict["practice_id"] = str(patient_dict["practice_id"])

        return patient_dict

    except DoesNotExist:
        # Handle the case when a patient with the given patient_id is not found
        pass


def retrieve_patients_by_ids(ids: List[str]):
    patients = []
    for patient_id in ids:
        try:
            # Retrieve the patient document based on patient_id
            patient_dict = retrieve_patient_by_id(patient_id)
            patients.append(patient_dict)

        except DoesNotExist:
            # Handle the case when a patient with the given patient_id is not found
            pass

    return patients


def update_patients_practice_id(patient_id: str, practice_id: str):
    try:
        patient = Patient.objects.get(id=patient_id)
        patient.practice_id = ObjectId(practice_id)
        patient.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Patient not found") from None


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
def create_new_letter(user_id: str, text: str, patient_id: str, tokens_consumed: Optional[int] = None):
    try:
        # user = User.objects.get(id=user_id)

        # Create a new Letter document
        letter = Letter(consent_letter=text, patient_id=patient_id, user_id=user_id, tokens_consumed=tokens_consumed)

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
        del patient_details["dob"]
        del patient_details["gender"]
        del patient_details["address"]
        del patient_details["email"]
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
def create_triage_request(practice_id: str, email: str, diagnosis: str, overview: str, severity: str, requested_date: str, GPT_QA: str):
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
    else:
        requested_date = None

    # Create a new triage request document for existing patient
    new_triage = Triage(
        practice_id=practice_id,
        patient_id=patient,
        diagnosis=diagnosis,
        general_overview=overview,
        severity=severity,
        requested_date=requested_date,
        GPT_QA=json.dumps(GPT_QA),
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
            .only("opened", "severity", "diagnosis", "patient_id", "practice_id")
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
            .only("opened", "severity", "diagnosis", "patient_id", "practice_id")
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


# Note ---------------------------
def create_audio_note(patient_id: str, user_id: str, practice_id: str, audio_bytesio: BytesIO, transcript: str, formatted_notes: str):
    try:
        # Convert BytesIO to bytes
        audio_bytes = audio_bytesio.getvalue()
        audio_note = AudioNote(
            patient_id=patient_id, user_id=user_id, practice_id=practice_id, audio=audio_bytes, transcript=transcript, formatted_notes=formatted_notes
        )
        audio_note.save()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


def delete_note(practice_id: str, file_id: str):
    note_to_delete = AudioNote.objects(id=file_id, practice_id=practice_id).first()

    if not note_to_delete:
        raise HTTPException(status_code=404, detail="No member with that id found in practice")

    # Delete the user document
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
def retrieve_note(note_id, user_id):
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
    del patient_details["email"]
    note_dict["patient_details"] = patient_details
    del note_dict["patient_id"]

    return note_dict


# Function to update the consent letter
def update_note(note_id, text, user_id: str):
    # Use MongoEngine to find and update the document
    note = AudioNote.objects(id=note_id, user_id=user_id).first()

    if not note:
        raise HTTPException(status_code=404, detail="No note found")

    # Update the consent_letter field
    note.formatted_notes = text
    note.save()


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
