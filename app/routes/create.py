import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from starlette_context import context

from app.middleware.jwt import JWTBearer
from app.models.create import SymptomData
from app.services.openAI import ask_gpt

router = APIRouter(prefix="/create", tags=["Create"])

log = logging.getLogger(__name__)

@router.post("/symptoms")
async def generateQuestions(body: SymptomData, request: Request, access_token=Depends(JWTBearer())):
    """
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    context["request_id"] = request_id

    print(f"Request: {request_id}")
    # store UNIX timestamp for when request is created
    context["created"] = datetime.now(timezone.utc).timestamp() * 1000

    patientDetails = json.loads(body.patientDetails)
    symptomDetails = json.loads(body.symptomDetails)
    symptomDetails = list(symptomDetails.values())

    log.info(f"Request {request_id} received for patient: {patientDetails['forename']} {patientDetails['surname']}.")
    log.info(f"Symptoms: {symptomDetails}")

    # Performs parallel calls to chatGPT
    async def process_symptom(symptom):
        prompt = f"""
            Patient symptom: {symptom}

            For the patient symptom above, I want you to ask 3 follow up questions to help identify ways to treat the symptom.
            These questions will then be answered by a dentist to help identify the cause of the patients symptom.
            Please format your response as JSON, as shown below:
            {{
                'symptom': [Symptom name],
                'q1': [Insert first question],
                'q2': [Insert second question],
                'q3': [Insert third question]
            }}
        """
        return await ask_gpt(prompt, "You're a helpful AI dentists assistant")

    # Stores parallel calls to chatGPT in array
    symptom_tasks = [process_symptom(symptom) for symptom in symptomDetails]
    responses = await asyncio.gather(*symptom_tasks)

    # Preprocess each response string
    preprocessed_responses = [response.replace("'", '"') for response in responses]

    # Parse each preprocessed response string as JSON
    json_responses = [json.loads(response) for response in preprocessed_responses]

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return json_responses



