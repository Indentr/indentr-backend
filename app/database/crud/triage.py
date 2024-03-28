# Triage CRUD file
# -- Files must start with either create, retrieve, update, delete

import json
from datetime import datetime
from typing import List

from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.patient import Patient, PatientName
from app.database.schemas.triage import Triage
from app.database.schemas.user import User


def create_triage_request(
    practice_id: str,
    email: str,
    diagnosis: str,
    reason_for_request: str = None,
    overview: str = None,
    severity: str = None,
    requested_date: str = None,
    GPT_QA: str = None,
    instruction: bool = False,
    patient_instruction: str = None,
):
    # Try to find the patient by email within the practice
    try:
        patient = Patient.objects.get(email=email, practice_id=practice_id)
    except Patient.DoesNotExist:
        # if the patient doesn't exist within the practice
        # Check if the patient already exists within our system
        try:
            patient = Patient.objects.get(email=email, practice_id=None)
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
        patient_instruction=patient_instruction,
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
