# Letter CRUD file
# -- Files must start with either create, retrieve, update, delete

from datetime import datetime
from string import ascii_lowercase

from bson import ObjectId
from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.letter import Letter
from app.database.schemas.patient import Patient, PatientName


def create_new_letter(
    user_id: str,
    text: str,
    patient_id: str,
    practice_id: str,
    input_tokens: int = None,
    output_tokens: int = None,
    cost: int = None,
    model: str = None,
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
            practice_id=practice_id,
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


def delete_letter(practice_id: str, file_id: str):
    letter_to_delete = Letter.objects(id=file_id, practice_id=practice_id).first()

    if not letter_to_delete:
        raise HTTPException(status_code=404, detail="No member with that id found in practice")

    # Delete the user document
    letter_to_delete.delete()


def retrieve_last_three_letters(user_id: str):
    try:
        letters = Letter.objects(user_id=user_id).only("consent_letter", "patient_id", "createdAt").order_by("-_id").limit(3).select_related()

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


def retrieve_all_users_letters(user_id: str = None, practice_id: str = None):
    try:
        if not user_id:
            letters = (
                Letter.objects(practice_id=practice_id).only("consent_letter", "patient_id", "createdAt").order_by("-createdAt").select_related()
            )
        else:
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


def retrieve_all_users_letters_filtered_by_char(starts_with: str, user_id: str = None, practice_id: str = None):
    try:
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
            {"$unwind": "$patient"},
            {"$match": {"patient.forename": {"$regex": f"^{starts_with}", "$options": "i"}}},
            {"$sort": {"createdAt": -1}},
        ]

        if practice_id:
            pipeline = [
                {"$match": {"practice_id": ObjectId(practice_id)}},
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


def retrieve_letters_alphabet_status(user_id: str = None, practice_id: str = None):
    try:
        # Use the aggregation framework to calculate alphabet status
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
            {"$unwind": "$patient"},
            {"$group": {"_id": {"$substr": ["$patient.forename", 0, 1]}, "count": {"$sum": 1}}},
        ]

        if practice_id:
            pipeline = [
                {"$match": {"practice_id": ObjectId(practice_id)}},
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
def retrieve_user_letter(letter_id: str, practice_id: str):
    # Query the letter using MongoEngine
    letter = Letter.objects(id=letter_id, practice_id=practice_id).first()

    if not letter:
        # Handle case where the letter doesn't exist or doesn't belong to the user
        raise HTTPException(status_code=400, detail="No letter found")

    created_at = letter.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
    letter_dict = letter.to_mongo().to_dict()
    letter_dict["createdAt"] = created_at
    letter_dict["_id"] = str(letter.id)
    letter_dict["practice_id"] = str(letter.practice_id)
    letter_dict["user_id"] = str(letter.user_id.id)
    letter_dict["patient_id"] = str(letter.patient_id.id)
    if "tokens_consumed" in letter_dict:
        del letter_dict["tokens_consumed"]

    return letter_dict


def retrieve_letter_count_for_billing_cycle(practice_id: str, start_date: datetime, end_date: datetime):
    letters_count = Letter.objects.filter(practice_id=practice_id, createdAt__gte=start_date, createdAt__lte=end_date).count()

    return letters_count


# Function to update the consent letter
def update_letter(letter_id, text, practice_id: str):
    # Use MongoEngine to find and update the document
    letter = Letter.objects(id=letter_id, practice_id=practice_id).first()

    if not letter:
        raise HTTPException(status_code=404, detail="No letter found")

    # Update the consent_letter field
    letter.consent_letter = text
    letter.save()
