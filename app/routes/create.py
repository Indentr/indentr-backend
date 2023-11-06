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
    # Generate Follow-Up Questions for Patient Symptoms, the questions should be focussed on what the dentist is going to
      need to know in order to better understand how to treat the patient.

    This endpoint generates follow-up questions for each symptom provided by the patient.
    It uses the GPT model to formulate the questions based on the provided symptom.

    ## Parameters

    - `body` (`SymptomData`): JSON data containing patient and symptom details.
    - `request` (`Request`): FastAPI request object.
    - `access_token` (`str, optional`): JWT access token. Defaults to `Depends(JWTBearer())`.

    ## Response

    A list of JSON objects containing follow-up questions for each symptom.

    ## Example Request

    ```http
    POST /symptoms HTTP/1.1
    Host: your-api-domain.com
    Content-Type: application/json
    Authorization: Bearer your-access-token

    {
      "symptomDetails": "{\"symptom1\": \"description1\", \"symptom2\": \"description2\", ...}"
    }
    ```

    ## Example Response
    ```json
    [
        {
            "symptom": "[Symptom name]",
            "q1": "[Insert q1]",
            "q2": "[q2]",
            "q3": "[q3]"
        },
        {
            "symptom": "[Another Symptom]",
            "q1": "[Insert q1]",
            "q2": "[q2]",
            "q3": "[q3]"
        },
        ...
    ]
    ```

    ## Errors
    HTTPException: If there are any errors during the process.

    This format presents the information clearly and concisely, making it easy for users to understand the purpose of the endpoint, its parameters, request and response examples, and potential errors.
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


@router.post("/treatmentPlan")
async def generate_treatment_plan(body: treatmentPlanData, request: Request, access_token=Depends(JWTBearer())):
    """
    # Generate Treatment Plan/informed consent letter based on Patient and Symptom Details
    This endpoint generates a treatment plan that doubles as an informed consent letter, tailored to the patient's symptoms.
    The treatment plan/informed consent letter is returned as an HTML-formatted string.

    ## Parameters
    - `body` (`treatmentPlanData`): JSON data containing patient and symptom details.
    - `request` (`Request`): FastAPI request object.
    - `access_token` (`str, optional`): JWT access token. Defaults to `Depends(JWTBearer())`.

    ## Response
    A formatted HTML (string) treatment plan, customized based on the provided patient and symptom details.

    ## Example Request
    ```http
    POST /treatmentPlan HTTP/1.1
    Host: your-api-domain.com
    Content-Type: application/json
    Authorization: Bearer your-access-token

    {
      "patientDetails": "{\"dob\": \"1990-01-01\", \"forename\": \"John\", \"surname\": \"Doe\", \"address\": \"123 Main St, City, Country\"}",
      "symptomDetails": "{\"symptom1\": \"description1\", \"symptom2\": \"description2\", ...}"
    }
    ```

    ## Example Response
    ```str
    '<p>123 Main St,</p>
    <p>City,</p>
    <p>Country,</p>
    <p></p>
    <p>Dear John Doe,</p>
    <p></p>
    <p>[HTML-formatted treatment plan]</p>'
    ```
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

        I want you to write a treatment plan that is also an informed consent letter for the patient above based on the symptom details provided.
        I have provided an example to use as a guide on how to structure a treatment plan letter. The aim of the letter is to provide the patient,
        with the information that they need to make a decision to go forward with the treatment. The letter should provide some information about the
        possible complications. The letter is, however, essentially a final sales pitch for the treatment that has already been discusssed in person
        with the patient.

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

    address = patientDetails["address"]
    address_parts = address.split(", ")

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

    return header + dear + treatmentPlan


@router.post("/createTreatmentPlan")
def create_treatment_plan(body: createTreatmentPlan, request: Request, access_token=Depends(JWTBearer())):
    """
    # Create Treatment Plan
    This endpoint allows the creation and saving of a treatment plan. The provided treatment plan content and patient details are saved to the database.

    ## Parameters
    - `body` (`createTreatmentPlan`): JSON data containing patient details and the treatment plan content.
    - `request` (`Request`): FastAPI request object.
    - `access_token` (`str, optional`): JWT access token. Defaults to `Depends(JWTBearer())`.

    ## Response
    - `message` (`str`): A message indicating the result of the operation ("Letter saved successfully" or "Failed to insert letter to files").
    - `letter_id` (`str`): The ID of the inserted letter if the operation was successful.

    ## Example Request
    ```http
    POST /createTreatmentPlan HTTP/1.1
    Host: your-api-domain.com
    Content-Type: application/json
    Authorization: Bearer your-access-token

    {
      "patientDetails": "{\"forename\": \"John\", \"surname\": \"Doe\"}",
      "treatmentPlan": "<p>HTML-formatted treatment plan</p>"
    }
    ```
    ## Example Response (Success)
    ```json
    {
      "message": "Letter saved successfully",
      "letter_id": "inserted-letter-id"
    }
    ```

    ## Example Response (Failure)
    ```json
    {
      "message": "Failed to insert letter to files"
    }
    ```

    ## Notes
    - This route requires an access token obtained through authentication.
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for saving treatment plan.")

    patientDetails = body.patientDetails
    treatmentPlan = body.treatmentPlan
    db = request.app.state.db
    token = decodeJWT(access_token)
    user_id = token["user_id"]
    letters_collection = db["letters"]

    letter_data = {"consent_letter": treatmentPlan, "patient_info": json.loads(patientDetails), "user_id": ObjectId(user_id)}

    result = letters_collection.insert_one(letter_data)

    if result.inserted_id:
        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return {"message": "Letter saved successfully", "letter_id": str(result.inserted_id)}
    else:
        log.debug(f"Request {request_id} failed and took in {round((time.time() - start), 2)} seconds.")
        return {"message": "Failed to insert letter to files"}
