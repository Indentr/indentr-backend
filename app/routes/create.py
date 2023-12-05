import json
import logging
import time
import uuid
import base64

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File

from app.database.crud import create_new_letter, retrieve_pricing, update_user_tokens
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.create import (
    SaveTreatmentPlan,
    SaveTreatmentPlanResponse,
    SymptomData,
    SymptomResponse,
    TreatmentPlanData,
    TreatmentPlanResponse,
)
from pydantic import BaseModel
from app.prompts import dentist_notes_prompt, symptoms_details_prompt
from app.services.openAI import ask_gpt, ask_gpt_image
from app.treatmentPlans.implantLetter import example_consent_letter

router = APIRouter(prefix="/create", tags=["Create"])

log = logging.getLogger(__name__)


@router.post("/generate_questions/{form_type}", response_model=list[SymptomResponse])
async def generate_questions(body: SymptomData, form_type: str, access_token=Depends(JWTBearer())):
    """
    # Generate Follow-Up Questions for Patient Symptoms
    This endpoint generates follow-up questions for each symptom provided by the patient.
    It uses the GPT model to formulate the questions based on the provided symptom.
    """
    start = time.time()
    request_id = uuid.uuid4().hex

    token = decodeJWT(access_token)
    user_id = token["user_id"]

    symptomDetails = json.loads(body.symptomDetails)

    if form_type == "symptom":
        symptomDetails = ", ".join(list(symptomDetails.values()))
        selected_prompt = symptoms_details_prompt

    else:
        selected_prompt = dentist_notes_prompt

    log.info(f"Request {request_id} received for symptom questions.")
    log.info(f"Symptoms: {symptomDetails}")

    prompt = f"""
        Patient's symptoms (dentist notes): {symptomDetails}

        {selected_prompt}
    """

    original_response, tokens = await ask_gpt(prompt, "You're an AI dental assistant")

    update_user_tokens(user_id, tokens)

    try:
        symptoms = json.loads(original_response)
    except json.JSONDecodeError as e:
        # Handle the case where json.loads fails, still send GPT response back as error message
        error_detail = f"Error decoding GPT response: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail) from e

    log.info(f"GPT symptoms response: {symptoms}")

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return symptoms

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
        raise HTTPException(status_code=500, detail="Failed to save image") from e

class AudioData(BaseModel):
    audioData: str  # Field to receive base64 encoded audio data

@router.post("/uploadAudio")
async def upload_audio(audioData: AudioData, access_token=Depends(JWTBearer())):
    print("Upload audio route called")

    try:
        # Decode the base64 string to bytes
        audio_bytes = base64.b64decode(audioData.audioData)

        # Generate a file name
        file_location = f"audio_uploads/{uuid.uuid4().hex}.wav"

        # Save the decoded audio
        with open(file_location, "wb") as file:
            file.write(audio_bytes)

        # Process the file as needed
        # For example, analyze the audio, transcribe, etc.

        return {"message": "File uploaded successfully (msg from server)", "filename": file_location}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
        
@router.post("/treatmentPlan", response_model=TreatmentPlanResponse)
async def generate_treatment_plan(body: TreatmentPlanData, access_token=Depends(JWTBearer())):
    """
    # Generates a treatment plan based on Patient and Symptom Details
    This endpoint generates a treatment plan tailored to the patient's symptoms. The treatment plan is returned as an HTML-formatted string.
    """

    start = time.time()
    request_id = uuid.uuid4().hex

    token = decodeJWT(access_token)
    user_id = token["user_id"]

    pricing_list = retrieve_pricing(user_id)

    patientDetails = json.loads(body.patientDetails)
    symptomDetails = json.loads(body.symptomDetails)
    dentistNotes = json.loads(body.dentistNotes)

    dentistNotesText = f"The patient notes, written by the dentist, are as as follows: {dentistNotes}"

    log.info(f"Request {request_id} received for s.")
    log.info(f"treatment plan details: {symptomDetails}")

    prompt = f"""

        Patient's dob: {patientDetails['dob']}
        Patient's symptoms: {symptomDetails}

        I want you to write a treatment plan that is also an informed consent letter for the patient above based on the symptom details provided.
        I have provided an example to use as a guide on how to structure a treatment plan letter. The aim of the letter is to provide the patient,
        with the information that they need to make a decision to go forward with the treatment. The letter should provide some information about the
        possible complications. The letter is, however, essentially a final sales pitch for the treatment that has already been discusssed in person
        with the patient.

        Please include a section that breaks down the cost of the planned treatments based on the provided dental practice pricing list.

        {dentistNotesText if dentistNotes != "" else ""}

        Example dental treatment plan consent letter:
        {example_consent_letter}

        Dental practice pricing list:
        {pricing_list}

        Your response must be written as an HTML string in the format provided below,
        where each paragraph is wrapped in a <p> tag:

        <p class="p1-title">[insert paragraph text, do not include dear ....]</p>
        <p></p> // IMPORTANT: for each new paragraph/section insert an empty p tag
        <p class="etc">[etc.]</p>

        // if letter requires an undordered list or bullet list then within a paragraph you can insert html for ul/ol
        <p class="insert-pX-title]">
            <ul>
                <li>[insert list item]</li>
                <li>[etc.]</li>
            </ul>
        </p>
        <p></p>
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

    treatmentPlan, tokens = await ask_gpt(prompt, "You're a UK based dentist writing treatment plan letters for patients")
    update_user_tokens(user_id, tokens)

    log.info(f"GPT treatment plan response: {treatmentPlan}")

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

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")
    return {"html_content": response_html, "tokens_consumed": tokens}

@router.post("/saveTreatmentPlan", response_model=SaveTreatmentPlanResponse)
def save_treatment_plan(body: SaveTreatmentPlan, access_token=Depends(JWTBearer())):
    """
    # Create Treatment Plan
    This endpoint allows the creation and saving of a treatment plan. The provided treatment plan content and patient details are saved to the database.
    """

    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.info(f"Request {request_id} received for saving treatment plan.")

        token = decodeJWT(access_token)
        user_id = token["user_id"]

        patient_details = body.patient_details
        treatment_plan = body.treatment_plan
        tokens_consumed = body.tokens_consumed

        result = create_new_letter(user_id, treatment_plan, patient_details, tokens_consumed)
        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")

        return {"message": "Letter saved successfully", "letter_id": str(result)}

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took in {round((time.time() - start), 2)} seconds.")
        raise e


