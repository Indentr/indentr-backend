import json
import logging
import os
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException

from app.database.crud import (
    create_triage_request,
    retrieve_practice_by_id,
    retrieve_patient_by_email
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.triage import GenerateQuestions, CreatePatientRequest
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
        practice = retrieve_practice_by_id(practice_id)

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
            if patient["practice_id"] != practice_id:
                raise HTTPException(status_code=404, detail="Email not associated with practice")

        except HTTPException as e:
            raise HTTPException(status_code=404, detail="Email not associated with practice")

    else:
        # if the patient is new then add them to the db but without a practice
        try:
            # check if the patient already exists within the system
            patient = retrieve_patient_by_email(patient_details["email"])
            
        except HTTPException as e:
            # if the patient doesn't exist then add them to the db
            create_new_patient(patient_details["forename"], patient_details["surname"], patient_details["dob"], patient_details["gender"], patient_details["address"], patient_details["email"])


    log.info(f"Request {request_id} received for triage symptom questions.")

    prompt = f"""
        Patient's symptom: {patient_details["symptom"]}

        Please ask the patient three follow-up questions.
        The questions show aim to gather more information from the patient so the dentist has all the necessary information in terms of severity of condition etc.
        Please format your response as JSON, as shown below:
        [
            {{
                "symptom": "[Symptom name]",
                "q1": "[Insert q1]",
                "q2": "[q2]",
                "q3": "[q3]"
            }},
            {{
                etc.
            }}
        ]
    """

    original_response, tokens = await ask_gpt(prompt, "You're an AI dental assistant")

    try:
        questions = json.loads(original_response)

    except json.JSONDecodeError as e:
        # Handle the case where json.loads fails, still send GPT response back as error message
        error_detail = f"Error decoding GPT response: {str(e)}"
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

    start = time.time()
    request_id = uuid.uuid4().hex

    patient_details = json.loads(body.patient_details)
    practice_id = json.loads(body.practice_id)
    symptom_details = json.loads(body.symptom_details)
    
    log.info(f"Request {request_id} received for creating a patient triage request.")

    prompt = f"""
        A patient has just filled out a dental triage form where they were asked 3 questions based on a dental symptom they have.
        The questions and patients answers: {symptom_details}

        Based on the patients patients response I need you to give a response to the following:
        1. A diagnosis title, a very short title of like 5 words max
        2. A general overview of the problem (max 100 words)
        3. A severity score out of 10 (10 being absolutely must see a dentist in the next hour or they will die, 1 being tooth hurts slightly)

        Your responses to the following must be formatted as JSON, as shown below:
        {{
            "diagnosis": "[Your diagnosis title],
            "overview": "[A general overview of the problem]",
            "severity": "[An int value between 0/10]":
        }}
    """

    original_response, tokens = await ask_gpt(prompt, "You're an AI dental assistant")

    try:
        response = json.loads(original_response)

    except json.JSONDecodeError as e:
        # Handle the case where json.loads fails, still send GPT response back as error message
        error_detail = f"Error decoding GPT response: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail) from e

    create_triage_request(practice_id, patient_details["email"], response["diagnosis"], response["overview"], response["severity"])

    return {"success": True}



