import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.database.crud import (
    retrieve_all_users_letters,
    retrieve_patients_by_ids,
    retrieve_user_letter,
    update_letter,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.file import saveTreatmentPlan

router = APIRouter(prefix="/files", tags=["Files"])

log = logging.getLogger(__name__)


@router.get("/")
def get_files(access_token=Depends(JWTBearer())):
    """
    This endpoint allows authenticated users to retrieve all of their treatment plans.
    """

    token = decodeJWT(access_token)
    user_id = token["user_id"]
    letters = retrieve_all_users_letters(user_id)
    letter_patient_ids = [letter.get("patient_id") for letter in letters]
    letter_patients = retrieve_patients_by_ids(letter_patient_ids)
    for index, request in enumerate(letters):
        request["patient_details"] = letter_patients[index]

    print("letters", letters)
    return {"letters": letters}


@router.get("/{letter_id}")
def get_treatment_plan(letter_id: str, access_token=Depends(JWTBearer())):
    """
    Retrieves a treatment plan based on the provided letter ID.
    """

    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        letter = retrieve_user_letter(letter_id, user_id)
        return letter

    except HTTPException as e:
        raise e


@router.post("/saveTreatmentPlan")
def save_treatment_plan(body: saveTreatmentPlan, access_token=Depends(JWTBearer())):
    """
    Saves a treatment plan to the database. If a letter with the provided ID
    exists, the consent letter field will be updated with the new treatment plan.
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for saving treatment plan.")

    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        letter_id = body.letterId
        treatmentPlan = body.treatmentPlan
        update_letter(letter_id, treatmentPlan, user_id)
        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return {"message": "Letter updated successfully"}

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took {round((time.time() - start), 2)} seconds.")
        log.debug(f"Request {request_id} Error: {e.detail}")
        raise e
