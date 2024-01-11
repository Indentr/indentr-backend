import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.database.crud import (
    create_new_patient,
    create_triage_request,
    delete_triage_requests,
    retrieve_all_triage_requests,
    retrieve_patient_by_email,
    retrieve_practice_by_id,
    retrieve_triage_request,
    update_patients_practice_id,
    update_triage_requests_opened,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.triage import (
    AddPatientToPractice,
    CreatePatientRequest,
    DeleteTriageRequests,
    GenerateQuestions,
    ToggleTriageOpenedRequest,
)
from app.prompts import create_triage_request_prompt, generate_triage_questions_prompt
from app.services.openAI import ask_gpt

router = APIRouter(prefix="/triage", tags=["Triage"])

# initiates logger
log = logging.getLogger(__name__)


@router.get("/{practice_id}")
def check_practice_id_valid(practice_id: str):
    """
    Checks if a practice_id is valid.
    """
    try:
        retrieve_practice_by_id(practice_id)

        return {"success": True}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/generate-questions")
async def generate_triage_questions(body: GenerateQuestions):
    """
    # Generates Follow-Up Questions for Patient Symptoms
    This endpoint generates follow-up questions for the symptom provided by the patient.
    It uses the GPT model to formulate the questions based on the provided symptom.
    """
    start = time.time()
    request_id = uuid.uuid4().hex

    patient_details = json.loads(body.patient_details)
    practice_id = json.loads(body.practice_id)

    if body.existing_patient:
        # check if email exists within that practice's list of patients
        try:
            patient = retrieve_patient_by_email(patient_details["email"])
            if "practice_id" not in patient or patient["practice_id"] != practice_id:
                raise HTTPException(status_code=404, detail="Email not associated with practice")

        except HTTPException as e:
            raise HTTPException(status_code=404, detail="Email not associated with practice") from e

    else:
        # if the patient is new then add them to the db but without a practice
        try:
            # check if the patient already exists within the system
            patient = retrieve_patient_by_email(patient_details["email"])

        except HTTPException:
            # if the patient doesn't exist then add them to the db
            create_new_patient(
                patient_details["forename"],
                patient_details["surname"],
                patient_details["dob"],
                patient_details["gender"],
                patient_details["address"],
                patient_details["email"],
            )

    log.info(f"Request {request_id} received for triage symptom questions.")

    prompt = f"""
        Reason for appointment request: {patient_details["appointment_reason"]}
        {generate_triage_questions_prompt}
    """

    original_response, tokens = await ask_gpt(prompt, "You're an AI dental assistant", "gpt-3.5-turbo")

    try:
        questions = json.loads(original_response)

    except json.JSONDecodeError as e:
        # Handle the case where json.loads fails, still send GPT response back as error message
        error_detail = f"Error decoding GPT response: {str(e)}"
        log.debug(f"Request {request_id} failed in {round((time.time() - start), 2)} seconds.")
        raise HTTPException(status_code=500, detail=error_detail) from e

    log.info(f"GPT questions response: {questions}")
    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return questions


@router.post("/create-patient-request")
async def create_patient_request(body: CreatePatientRequest):
    """
    # Creates a patient request in the database
    Take the symptom details and get LLM to turn it into specified patient request.
    The response is then saved to the triage table in mongoDB.
    """

    time.time()
    request_id = uuid.uuid4().hex

    patient_details = json.loads(body.patient_details)
    practice_id = json.loads(body.practice_id)
    symptom_details = json.loads(body.symptom_details)

    log.info(f"Request {request_id} received for creating a patient triage request.")

    prompt = f"""
        The questions and patients answers: {symptom_details}
        {create_triage_request_prompt}
    """

    original_response, tokens = await ask_gpt(prompt, "You're an AI dental assistant", "gpt-3.5-turbo")

    try:
        response = json.loads(original_response)

    except json.JSONDecodeError as e:
        # Handle the case where json.loads fails, still send GPT response back as error message
        error_detail = f"Error decoding GPT response: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail) from e

    create_triage_request(
        practice_id,
        patient_details["email"],
        response["diagnosis"],
        response["overview"],
        response["severity"],
        patient_details["requested_date"],
        symptom_details,
    )

    return {"success": True}


@router.get("/get-requests/")
async def get_all_triage_requests(access_token=Depends(JWTBearer())):
    """
    # Gets all practice's triage requests
    Finds the practice id based on user's access token.
    Returns all triage requests for that practice
    """

    start = time.time()
    request_id = uuid.uuid4().hex

    log.debug(f"Request {request_id} received for getting all practice's triage requests.")

    token = decodeJWT(access_token)
    practice_id = token["practice_id"]

    triage_requests = retrieve_all_triage_requests(practice_id)

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return {"triage_requests": triage_requests}


@router.get("/get-request/{triage_id}")
async def get_triage_request(triage_id: str, access_token=Depends(JWTBearer())):
    """
    # Gets a triage request based on id.
    Returns triage request
    """

    start = time.time()
    request_id = uuid.uuid4().hex

    log.debug(f"Request {request_id} received for getting all practice's triage requests.")

    token = decodeJWT(access_token)
    practice_id = token["practice_id"]

    triage_request = retrieve_triage_request(triage_id, practice_id)

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return {"triage_request": triage_request}


@router.post("/toggle-unread/")
async def toggle_triage_request_opened(body: ToggleTriageOpenedRequest, access_token=Depends(JWTBearer())):
    """
    # Toggles selected triage requests to be opened/closed
    Finds the practice id based on user's access token.
    Sets all selected triage requests to be opened or closed
    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.debug(f"Request {request_id} received for toggling triage requests to be opened/closed.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        triage_requests = json.loads(body.selected_requests)
        opened = json.loads(body.opened)

        update_triage_requests_opened(triage_requests, opened, practice_id)

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {"success": True}

    except HTTPException as e:
        raise e


@router.post("/delete-requests/")
async def delete_selected_triage_requests(body: DeleteTriageRequests, access_token=Depends(JWTBearer())):
    """
    # Deletes the selected triage requests

    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.debug(f"Request {request_id} received for toggling triage requests to be opened/closed.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        triage_requests = json.loads(body.selected_requests)

        delete_triage_requests(triage_requests, practice_id)

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {"success": True}

    except HTTPException as e:
        raise e


@router.post("/add-patient-to-practice/")
async def add_new_patient_to_practice(body: AddPatientToPractice, access_token=Depends(JWTBearer())):
    """
    # Assigns a new patient to be part of a dental practice
    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.debug(f"Request {request_id} received for adding a new patient to a practice.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]
        patient_id = json.loads(body.patient_id)

        update_patients_practice_id(patient_id, practice_id)

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {"success": True, "message": "Added patient to practice!"}

    except HTTPException as e:
        raise e
