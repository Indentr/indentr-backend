# Patient CRUD file
# -- Files must start with either create, retrieve, update, delete

from string import ascii_lowercase
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.audio_note import AudioNote
from app.database.schemas.letter import Letter
from app.database.schemas.patient import Patient
from app.database.schemas.triage import Triage


def create_new_patient(forename: str, surname: str, dob: str, gender: str, address: str, email: str, practice_id: Optional[str] = None):
    # try:
    # Check if a patient with the same email already exists
    existing_patient = Patient.objects(email=email, practice_id=practice_id).first()
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


def retrieve_patient_by_email(email: str, practice_id: str):
    try:
        # Retrieve the patient document based on email
        patient = Patient.objects.get(email=email, practice_id=practice_id)

        patient_dict = patient.to_mongo().to_dict()
        if "practice_id" in patient_dict:
            patient_dict["practice_id"] = str(patient_dict["practice_id"])
            if "dob" in patient_dict:
                patient_dict["dob"] = patient.dob.strftime("%Y-%m-%d")

        return patient_dict

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Patient not found") from None


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
