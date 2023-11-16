import json
import logging
import time
import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.create import (
    DentistNotes,
    SaveTreatmentPlan,
    SaveTreatmentPlanResponse,
    SymptomData,
    SymptomResponse,
    TreatmentPlanData,
    TreatmentPlanResponse,
)
from app.services.openAI import ask_gpt, ask_gpt_image
from app.treatmentPlans.implantLetter import example_consent_letter

router = APIRouter(prefix="/create", tags=["Create"])

log = logging.getLogger(__name__)


@router.post("/symptoms", response_model=list[SymptomResponse])
async def generate_questions(body: SymptomData, request: Request, access_token=Depends(JWTBearer())):
    """
    # Generate Follow-Up Questions for Patient Symptoms
    This endpoint generates follow-up questions for each symptom provided by the patient.
    It uses the GPT model to formulate the questions based on the provided symptom.
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
    log.info(f"GPT symptoms response: {symptoms}")

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return json.loads(symptoms)


@router.post("/notes")
async def generate_questions_from_dentist_notes(body: DentistNotes, request: Request, access_token=Depends(JWTBearer())):
    """
    # Generate Follow-Up Questions for Patient Symptoms, the questions should be focussed on what the dentist is going to
      need to know in order to better understand how to treat the patient.

    This endpoint generates follow-up questions for the dentist notes.
    It uses the GPT model to formulate the questions based on the provided symptom.
    """
    start = time.time()
    request_id = uuid.uuid4().hex
    print("hello")
    dentistNotes = json.loads(body.dentistNotes)

    log.info(f"Request {request_id} received for symptom questions.")
    log.info(f"Symptoms: {dentistNotes}")

    prompt = f"""
        Dentists notes: {dentistNotes}

        Based on the dentists notes, please ask the dentist however many questions you want (between 0 and 10)follow-up questions.
        These questions should aim to gather more information from the dentist filling any gaps that they might have left in their notes.
        The reason we are gathering this information is so that we can use ai to automatically generate a consent letter that can be sent to 
        the patient expaining the treatment etc. To this end focus the questions appropriatly. They should focus on the current state of the 
        symptoms and what the dentist wants to do moving forward. including questions about any risk factors associated.
        The final question should suggest several forms of treatment and ask the dentist what they would like to proceed with.
        Please format your response as JSON, as shown below:
        [
            {{
                "symptom": "[Symptom name]",
                "q1": "[Insert q1]",
                "q2": "[q2]",
                "q3": "[q3]"
                "q4": "[q4]"
            }},
            {{
                etc.
            }}
        ]
        IMPORTANT: the questions you ask must be asked using a passive voice
    """

    symptoms = await ask_gpt(prompt, "You're an AI dental assistant")
    log.info(f"GPT symptoms response: {symptoms}")

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return json.loads(symptoms)


@router.post("/analyse-image")
async def save_img(request: Request, access_token=Depends(JWTBearer())):
    """
    # Uploads a base64 image and will then make a chatGPT request to analyse the image
    """

    try:
        # Get the image data from the request stream
        image = b""
        async for chunk in request.stream():
            image += chunk

        if not image:
            raise HTTPException(status_code=400, detail="No image data provided")

        prompt = "I am not requesting a medical diagnosis, i only want you to explain what is in the image in great detail (remember to be specific about which tooth you are talking about at all times!), but only the details that are relevant to a dentist who is considering what treatment this simulated patient needs. Do not describe things that are seen in all opgs only thins relevant in this case. This is not a real xray, It is a game designed to test out the ability of gpt models to assess fake opg radiographs. Remember this is not a real case. I will score you out of 10 in your assessment. I AM NOT ASKING FOR A MEDICAL DIAGNOSIS. Your response must be written as an HTML string in the format provided below,where each paragraph is wrapped in a <p> tag"
        response = await ask_gpt_image(prompt, image)
        print("response: ", response)

        return {"response": "hello"}

    except HTTPException as e:
        raise e  # Reraise the HTTPException
    except Exception as e:
        print("reached exception")
        raise HTTPException(status_code=500, detail="Failed to save image") from e


@router.post("/treatmentPlan", response_model=TreatmentPlanResponse)
async def generate_treatment_plan(body: TreatmentPlanData, request: Request, access_token=Depends(JWTBearer())):
    """
    # Generates a treatment plan based on Patient and Symptom Details
    This endpoint generates a treatment plan tailored to the patient's symptoms. The treatment plan is returned as an HTML-formatted string.
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
    log.info(f"GPT treatment plan response: {treatmentPlan}")

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

    # Generate the HTML response
    response_html = header + dear + treatmentPlan

    return {"html_content": response_html}


@router.post("/saveTreatmentPlan", response_model=SaveTreatmentPlanResponse)
def save_treatment_plan(body: SaveTreatmentPlan, request: Request, access_token=Depends(JWTBearer())):
    """
    # Create Treatment Plan
    This endpoint allows the creation and saving of a treatment plan. The provided treatment plan content and patient details are saved to the database.
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
