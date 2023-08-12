import json
import logging
import time
import uuid

from fastapi import APIRouter, Depends, Request

from app.middleware.jwt import JWTBearer
from app.models.create import SymptomData
from app.services.openAI import ask_gpt

router = APIRouter(prefix="/create", tags=["Create"])

log = logging.getLogger(__name__)

# @router.post("/symptoms")
# async def generate_questions(body: SymptomData, request: Request, access_token=Depends(JWTBearer())):
#     """
#     Generate follow-up questions for patient symptoms.

#     This endpoint generates follow-up questions for each symptom provided by the patient.
#     It uses the GPT model to formulate the questions based on the provided symptom.

#     Args:
#     - body (`SymptomData`): JSON data containing patient and symptom details.
#     - request (`Request`): FastAPI request object.
#     - access_token (`str, optional`): JWT access token. Defaults to `Depends(JWTBearer())`.

#     Returns:
#     - A list of `JSON objects` containing follow-up questions for each symptom.
#     """


#     start = time.time()
#     request_id = uuid.uuid4().hex

#     symptomDetails = json.loads(body.symptomDetails)
#     symptomDetails = list(symptomDetails.values())

#     log.info(f"Request {request_id} received for symptom questions.")
#     log.info(f"Symptoms: {symptomDetails}")

#     # Performs call to chatGPT based on prompt
#     async def process_symptom(symptom):
#         prompt = f"""
#             Patient symptom: {symptom}

#             I want you to ask 3 follow up questions to help identify ways a dentist can treat the symptom.
#             Please format your response as JSON, as shown below:
#             {{
#                 symptom: [Symptom name],
#                 q1: [Insert q1],
#                 q2: [q2],
#                 q3: [q3]
#             }}
#         """
#         return await ask_gpt(prompt, "You're a helpful AI dental assistant")

#     # Stores parallel calls to chatGPT in array
#     symptom_tasks = [process_symptom(symptom) for symptom in symptomDetails]
#     responses = await asyncio.gather(*symptom_tasks)

#     # Parse each preprocessed response string as JSON
#     json_responses = [json.loads(response) for response in responses]

#     log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

#     return json_responses



@router.post("/symptoms")
async def generate_questions(body: SymptomData, request: Request, access_token=Depends(JWTBearer())):
    """
    Generate follow-up questions for patient symptoms.

    This endpoint generates follow-up questions for each symptom provided by the patient.
    It uses the GPT model to formulate the questions based on the provided symptom.

    Args:
    - body (`SymptomData`): JSON data containing patient and symptom details.
    - request (`Request`): FastAPI request object.
    - access_token (`str, optional`): JWT access token. Defaults to `Depends(JWTBearer())`.

    Returns:
    - A list of `JSON objects` containing follow-up questions for each symptom.
    """


    start = time.time()
    request_id = uuid.uuid4().hex

    symptomDetails = json.loads(body.symptomDetails)
    symptomDetails = list(symptomDetails.values())

    log.info(f"Request {request_id} received for symptom questions.")
    log.info(f"Symptoms: {symptomDetails}")

    prompt = f"""
        Patient symptom: {', '.join(symptomDetails)}

        For each symptom I want you to ask 3 follow up questions to help identify ways a dentist can treat the symptom.
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

    symptoms = await ask_gpt(prompt, "You're a helpful AI dental assistant")

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return json.loads(symptoms)



