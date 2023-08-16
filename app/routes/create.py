import json
import logging
import time
import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, Request

from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.create import SymptomData, createTreatmentPlan, treatmentPlanData
from app.services.openAI import ask_gpt
from app.treatmentPlans.implantLetter import example_consent_letter

router = APIRouter(prefix="/create", tags=["Create"])

log = logging.getLogger(__name__)

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
        Patient's symptom: {', '.join(symptomDetails)}

        For each symptom, please ask the dentist three follow-up questions.
        These questions should aim to gather more information from the dentist about the patient's symptoms.
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
        IMPORTANT: the questions you ask must be asked using a passive voice
    """

    symptoms = await ask_gpt(prompt, "You're an AI dental assistant")

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return json.loads(symptoms)




@router.post("/treatmentOverview")
async def generate_treatment_overview(body: treatmentPlanData, request: Request, access_token=Depends(JWTBearer())):
    """
    Generate a treatment overview based on patient and symptom details.

    - **patientDetails**: A JSON string containing patient details.
    - **symptomDetails**: A JSON string containing symptom details.

    Returns a JSON response containing diagnosis, further investigations recommendations, and a treatment plan
    based on the patient's symptom data.

    **Note**: This route requires an access token obtained through authentication.

    ### Response:
    A JSON response containing diagnosis, further investigations recommendations, and a treatment plan.

    Example response:

    ```json
    {
        "Diagnosis": {
            "s1": {
                "d1": "[insert diagnosis of symptom 1]"
            },
            "s2": {
                "d1": "[insert diagnosis of symptom 2]"
            }
        },
        "Further investigations": {
            "s1": {
                "inv1": "[insert investigation 1]"
            },
            "s2": {}
        },
        "Treatment plan": {
            "plan1": {
                "1": "[insert step 1 for symptom 1]"
            },
            "plan2": {
                "1": "[insert step 1 for symptom 2]"
            }
        }
    }
    """

    start = time.time()
    request_id = uuid.uuid4().hex

    patientDetails = json.loads(body.patientDetails)
    symptomDetails = json.loads(body.symptomDetails)

    log.info(f"Request {request_id} received for generating treatment overview.")
    log.info(f"Patient details: {patientDetails}")
    log.info(f"treatment plan details: {symptomDetails}")

    prompt = f"""
        The patient was born {patientDetails['dob']} and their gender is {patientDetails['gender']}.
        Patient's symptoms data:

        {symptomDetails}

        Each JSON object contains the symptom name along with questions and responses.
        The questions and responses help to try and highlight the potential best course of treatment for that symptom.

        Based on the provided patient's symptom data,
        please provide a diagnosis, further investigations recomendations and a treatment plan.
        example response based on two symptoms (number of symptoms can range from 1 to n):
        {{
            "Diagnosis": {{
                "s1": {{
                    "d1": "[insert diagnosis of symptom 1]",
                }}
                 "s1": {{
                    "d1": "etc.",
                }}
            }},
            "Further investigations": {{
                "s1": {{
                    "inv1": "[insert investigation 1]", // leave empty if you think symptom doesn't warrant further investigation
                    "etc.": "[etc.]"
                }},
                "s2": {{
                    "etc": "[etc.]" // leave empty if you think symptom doesn't warrant further investigation
                }}
            }},
            "Treatment plan": {{
                "plan1": {{
                    "1":[insert step 1 for symptom 1]",
                    "etc.": "[etc.]",

                }},
                "plan2": {{
                    "1": "[insert step 1 for symptom 2]",
                    "etc.": "[etc.]",
                }}
            }}
        }}

        Your response must be in a valid JSON format, like the example JSON response above.
    """

    treatmentGuide = await ask_gpt(prompt, "You're a helpful AI dental assistant")

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return json.loads(treatmentGuide)







@router.post("/treatmentPlan")
async def generate_treatment_plan(body: treatmentPlanData, request: Request, access_token=Depends(JWTBearer())):
    """
    Generates a treatment plan based on patient and symptom details.

    - **patientDetails**: A JSON string containing patient details.
    - **symptomDetails**: A JSON string containing symptom details.

    Returns an HTML-formatted treatment plan tailored to the patient's symptoms.

    **Note**: This route requires an access token obtained through authentication.

    ### Response:
    A formatted HTML treatment plan.
    """

    start = time.time()
    request_id = uuid.uuid4().hex

    patientDetails = json.loads(body.patientDetails)
    symptomDetails = json.loads(body.symptomDetails)

    log.info(f"Request {request_id} received for s.")
    log.info(f"Patient details: {patientDetails}")
    log.info(f"treatment plan details: {symptomDetails}")

    prompt = f"""

        Patient's dob: {patientDetails['dob']}
        Patient's symptoms: {symptomDetails}

        I want you to write a treatment plan for the patient above based on the symptom details provided.
        I have provided an example to use as a guide on how to structure a treatment plan letter.

        Example dental treatment plan consent letter:
        {example_consent_letter}

        Your response must be written as an HTML string in the format provided below,
        where each paragraph is wrapped in a <p> tag:

        <p class="p1-title">[insert paragraph text, do not include dear ....]</p>
        <p></p> // insert empty p for a newline between each section
        <p class="etc">[etc.]</p>

        // if letter requires an undordered list or bullet list then within a paragraph you can insert html for ul/ol
        <p class="insert-pX-title]">
            <ul>
                <li>[insert list item]</li>
                <li>[etc.]</li>
            </ul>
        </p>
        <p class="insert-pX-title]">
            <ol>
                <li>[insert list item]</li>
                <li>[etc.]</li>
            </ol>
        </p>

        Using the example dental treatment plan consent letter as a template, I want you to tailor it
        so it uses the patient's symptoms I have given above (Make sure to remove or
        change unnecessary content from example letter so it fits the patient symptoms)

    """

    treatmentPlan = await ask_gpt(prompt, "You're a UK based dentist writing treatment plan letters for patients")

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    address = patientDetails['address']
    address_parts = address.split(', ')

    # Generate the HTML lines dynamically
    html_lines = "\n".join([f"<p>{part},</p>" for part in address_parts])

    # Format the address into the HTML string
    header = (f"""{html_lines}""") + ("<p></p>")

    dear = f"""
    <p>
        Dear {patientDetails['forename']} {patientDetails['surname']},
    </p>
    <p></p>
    """

    return (header + dear + treatmentPlan)




@router.post("/createTreatmentPlan")
def create_treatment_plan(body: createTreatmentPlan, request: Request, access_token=Depends(JWTBearer())):
    """
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for saving treatment plan.")

    patientDetails = body.patientDetails
    treatmentPlan = body.treatmentPlan
    db = request.app.state.db
    token = decodeJWT(access_token)
    user_id = token['user_id']
    letters_collection = db['letters']

    letter_data = {
        "consent_letter": treatmentPlan,
        "patient_info": json.loads(patientDetails),
        "user_id": ObjectId(user_id)
    }

    result = letters_collection.insert_one(letter_data)

    if result.inserted_id:
        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return {"message": "Letter saved successfully", "letter_id": str(result.inserted_id)}
    else:
        log.debug(f"Request {request_id} failed and took in {round((time.time() - start), 2)} seconds.")
        return {"message": "Failed to insert letter to files"}


