import json
import logging
import time
from datetime import datetime
import uuid
from io import BytesIO

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.constants import DB_URI
from app.database.atlas_search import atlas_search
from app.database.crud import (
    create_audio_note,
    create_new_letter,
    create_new_patient,
    retrieve_letter_config,
    retrieve_patient_by_email,
    retrieve_practice_by_id,
    retrieve_pricing,
    retrieve_prompt_by_title,
    retrieve_user_by_id,
    retrieve_vector_letters,
    update_user_tokens,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.create import (
    PatientDetails,
    PatientSearch,
    SaveFile,
    SaveFileResponse,
    SymptomData,
    SymptomResponse,
    TreatmentPlanData,
    TreatmentPlanResponse,
)
from app.services.deepgram import dpg_speech_to_text
from app.services.openAI import ask_gpt, ask_gpt_image, generate_embedding

# initiates api router
router = APIRouter(prefix="/create", tags=["Create"])

# initiates logger
log = logging.getLogger(__name__)


@router.post("/search-patients")
async def search_patients(body: PatientSearch, access_token=Depends(JWTBearer())):
    """
    # Searches the practice's list of patients for a match
    Uses the mongodb search functionality to get top 3/4 closest patient matches.
    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.info(f"Request {request_id} received for saving patient details.")

        token = decodeJWT(access_token)
        token["user_id"]
        practice_id = token["practice_id"]

        search_param = body.search_param
        pipeline = [
            {
                "$search": {
                    "index": "default",
                    "compound": {
                        "should": [
                            {"autocomplete": {"query": search_param, "path": "forename"}},
                            {"autocomplete": {"query": search_param, "path": "surname"}},
                            {"autocomplete": {"query": search_param, "path": "email"}},
                        ],
                        "filter": [
                            {"equals": {"value": ObjectId(practice_id), "path": "practice_id"}},
                        ],
                        "minimumShouldMatch": 1,
                    },
                }
            },
            {"$limit": 4},
            {
                "$project": {
                    "_id": 1,
                    "forename": 1,
                    "surname": 1,
                    "dob": 1,
                    "gender": 1,
                    "address": 1,
                    "email": 1,
                }
            },
        ]
        result = atlas_search(DB_URI, "patients", pipeline)

        for i in result:
            i["_id"] = str(i["_id"])

        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")

        return result

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took in {round((time.time() - start), 2)} seconds.")
        raise e


@router.post("/save-patient-details")
async def save_patient_details(body: PatientDetails, access_token=Depends(JWTBearer())):
    """
    # Saves the patient details to the DB
    This endpoint saves patient details to the DB based on the users practice_id.
    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.info(f"Request {request_id} received for saving patient details.")

        token = decodeJWT(access_token)
        token["user_id"]
        practice_id = token["practice_id"]

        patient_details = json.loads(body.patientDetails)

        create_new_patient(
            patient_details["forename"],
            patient_details["surname"],
            patient_details["dob"],
            patient_details["gender"],
            patient_details["address"],
            patient_details["email"],
            practice_id,
        )

        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")

        return {"message": "Patient details saved successfully"}

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took in {round((time.time() - start), 2)} seconds.")
        raise e


@router.post("/generate-questions", response_model=list[SymptomResponse])
async def generate_questions(body: SymptomData, access_token=Depends(JWTBearer())):
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
    symptomDetails = ", ".join(list(symptomDetails.values()))

    symptoms_details_prompt = retrieve_prompt_by_title("symptoms_details")

    log.info(f"Request {request_id} received for symptom questions. Symptoms: {symptomDetails}")

    prompt = f"""
        Patient's symptoms (dentist notes): {symptomDetails}

        {symptoms_details_prompt}
    """

    original_response, tokens = await ask_gpt(prompt, "You're an AI dental assistant", "gpt-3.5-turbo")
    update_user_tokens(user_id, tokens)

    try:
        questions = json.loads(original_response)
    except json.JSONDecodeError as e:
        # Handle the case where json.loads fails, still send GPT response back as error message
        error_detail = f"Error decoding GPT response: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail) from e

    log.info(f"GPT symptoms response: {questions}")

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return questions


@router.post("/consent-letter", response_model=TreatmentPlanResponse)
async def generate_treatment_plan(body: TreatmentPlanData, access_token=Depends(JWTBearer())):
    """
    # Generates a treatment plan based on Patient and Symptom Details
    This endpoint generates a treatment plan tailored to the patient's symptoms. The treatment plan is returned as an HTML-formatted string.
    """

    start = time.time()
    request_id = uuid.uuid4().hex

    token = decodeJWT(access_token)
    user_id = token["user_id"]
    practice_id = token["practice_id"]

    embedding = await generate_embedding(body.dentistNotes if body.dentistNotes else body.symptomDetails)
    pipeline = [
        {
            "$vectorSearch": {
                "index": "default",
                "queryVector": embedding,
                "path": "plot_embedding",
                "numCandidates": 100,
                "limit": 1,
            }
        },
        {"$project": {"consent_letter": 1, "_id": 0}},
    ]

    example_consent_letter = retrieve_vector_letters(pipeline)
    generate_consent_letter_prompt = retrieve_prompt_by_title("generate_consent_letter")
    letter_config = retrieve_letter_config(practice_id)

    if letter_config['pricing']:
        pricing_list = retrieve_pricing(practice_id)


    patientDetails = json.loads(body.patientDetails)
    symptomDetails, dentistNotes, dentistNotesText = None, None, None

    if body.symptomDetails:
        symptomDetails = json.loads(body.symptomDetails)

    if body.dentistNotes:
        dentistNotes = json.loads(body.dentistNotes)
        dentistNotesText = f"The patient notes, written by the dentist, are as as follows: {dentistNotes}"

    log.info(f"Request {request_id} received.")

    prompt = f"""

        Patient's dob: {patientDetails['dob']}
        { "Patient's symptoms:"+ str(symptomDetails) if symptomDetails else "" }
        {dentistNotesText if dentistNotes != "" else ""}

        Example dental consent letter:
        {example_consent_letter[0]["consent_letter"]}

        {"Dental practice pricing list:"+ str(pricing_list) if letter_config["pricing"] else "Don't include any pricing section/information"}

        {"Make sure to include both dentist and patient signature lines within the consent letter" if letter_config["patient_signature"] and letter_config["dentist_signature"] else ""}
        {"Make sure to include only dentist signature line (no patient signature line within the consent letter)" if letter_config["dentist_signature"] else ""}
        {"Make sure to include only patient signature line (no patient signature line within the consent letter)" if letter_config["patient_signature"] else ""}

        {generate_consent_letter_prompt}
    """
    gpt_model = "gpt-4-1106-preview"
    treatmentPlan, tokens = await ask_gpt(prompt, "You're a UK based dentist writing consent letters for patients", gpt_model)
    update_user_tokens(user_id, tokens)

    treatmentPlan = treatmentPlan[7:-3]
    log.info(f"GPT treatment plan response: {treatmentPlan}")

    header = ""
    date = ""
    if letter_config["patient_address"]:
        address = patientDetails["address"]
        address_parts = address.split(", ")
        # generates the HTML lines dynamically
        html_lines = "\n".join([f"<p style='text-align: right'>{part},</p>" for part in address_parts])
        # formats the address into the HTML string
        header = (f"""{html_lines}""") + ("<p></p><p></p>")

    if letter_config["date"]:
        current_date = datetime.now()
        uk_date_format = current_date.strftime("%d/%m/%y")
        date = f"""
            <p>
                {uk_date_format},
            </p>
            <p></p>
        """

    mrOrMrs = 'Mr' if patientDetails['gender'] else 'Mrs'

    dear = f"""
        <p>
            {letter_config["salutation"]} {patientDetails['forename'] if letter_config["recipient_naming"] == 'first_lastname' else mrOrMrs} {patientDetails['surname']},
        </p>
        <p></p>
    """

    # consent_lines = 

    user, practice = None, None
    if letter_config["dentist_naming"] == "practice_name" or letter_config["dentist_naming"] == "dentist_practice_name" or letter_config["practice_contact_details"]:
        practice = retrieve_practice_by_id(practice_id)

    if letter_config["dentist_naming"] == "dentist_name" or letter_config["dentist_naming"] == "dentist_practice_name":
        user = retrieve_user_by_id(user_id)

    signoff = f"""
        <p></p>
        <p>
            {letter_config["sign_off"]} {user['name'] if letter_config["dentist_naming"] == 'dentist_name' else ''} {(user['name']+', '+practice["practice_name"])  if letter_config["dentist_naming"] == 'dentist_practice_name' else ''} {practice["practice_name"] if letter_config["dentist_naming"] == 'practice_name' else ''}
        </p>
    """

    completed_in = f"""
        <p></p>
        <p>
            completed in {round((time.time() - start), 2)} seconds
        </p>
        <p/>
        <p>
            cost: {tokens} tokens
        </p>
        <p/>
        <p>
            used gpt model: {gpt_model}
        </p>
    """

    # Generate the HTML response
    response_html = header + date + dear + treatmentPlan + signoff + completed_in

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")
    return {"html_content": response_html, "tokens_consumed": tokens}


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
        print(response)

        return {"response": "hello"}

    except HTTPException as e:
        raise e  # Reraise the HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save image") from e


@router.post("/uploadTranscript")
async def upload_transcript(
    audioFile: UploadFile = File(...), transcript: str = Form(...), patientEmail: str = Form(...), access_token=Depends(JWTBearer())
):
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.info(f"Request {request_id} received for uploadAudio endpoint. Received file: transcript")

        token = decodeJWT(access_token)
        user_id = token["user_id"]
        practice_id = token["practice_id"]

        patient = retrieve_patient_by_email(patientEmail)
        patient_id = patient["_id"]

        upload_transcript_prompt = retrieve_prompt_by_title("upload_transcript")

        # Read the file contents into a memory buffer
        audio_content = await audioFile.read()
        # Create a BytesIO object to mimic file reading
        audio_buffer = BytesIO(audio_content)

        # AI formatting of dental voice notes
        prompt = f"""
            START OF TRANSCRIPT

            {transcript}

            END OF TRANSCRIPT

            {upload_transcript_prompt}
        """
        formatted_notes, tokens = await ask_gpt(prompt, "You're an ai formatting dental voice notes", "gpt-4-1106-preview")

        create_audio_note(patient_id, user_id, practice_id, audio_buffer, transcript, formatted_notes)

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        # Convert ObjectId to string for JSON serialization
        return {
            "formatted_notes": formatted_notes,
        }

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/uploadAudioTranscription")
async def upload_audio(audioFile: UploadFile = File(...), access_token=Depends(JWTBearer())):
    try:
        time.time()
        request_id = uuid.uuid4().hex

        log.info(
            f"Request {request_id} received for uploadAudioTranscription endpoint. Received file: {audioFile.filename}, Content type: {audioFile.content_type}"
        )

        decodeJWT(access_token)

        # Read the file contents into a memory buffer
        audio_content = await audioFile.read()
        # Create a BytesIO object to mimic file reading
        audio_buffer = BytesIO(audio_content)

        # Speech to text conversion
        response = await dpg_speech_to_text(audio_buffer)
        transcript = response.results.channels[0].alternatives[0].transcript

        # Convert ObjectId to string for JSON serialization
        return {
            "transcripts": transcript,
        }

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/save-file", response_model=SaveFileResponse)
def save_file(body: SaveFile, access_token=Depends(JWTBearer())):
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

        patient_details = json.loads(body.patient_details)
        treatment_plan = json.loads(body.treatment_plan)
        tokens_consumed = body.tokens_consumed

        patient = retrieve_patient_by_email(patient_details["email"])

        result = create_new_letter(user_id, treatment_plan, patient["_id"], tokens_consumed)
        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")

        return {"message": "Letter saved successfully", "letter_id": str(result)}

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took in {round((time.time() - start), 2)} seconds.")
        raise e
