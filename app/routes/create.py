import asyncio
import json
import logging
import time
import uuid
from io import BytesIO

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.constants import DB_URI
from app.database.atlas_search import atlas_search
from app.database.crud.audio_note import (
    create_audio_note,
    retrieve_audio_note_time_for_billing_cycle,
)
from app.database.crud.config import retrieve_prompt_by_title
from app.database.crud.custom_prompt import (
    retrieve_all_users_prompts,
    retrieve_prompt_with_prompt_id,
)
from app.database.crud.letter import (
    create_new_letter,
    retrieve_letter_count_for_billing_cycle,
)
from app.database.crud.letter_config import (
    retrieve_letter_config,
)
from app.database.crud.patient import create_new_patient, retrieve_patient_by_email
from app.database.crud.practice import retrieve_practice_by_id
from app.database.crud.pricing import retrieve_pricing
from app.database.crud.user import retrieve_user_by_id
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.create import (
    FormatTranscript,
    LetterData,
    LetterResponse,
    PatientDetails,
    PatientSearch,
    SaveFile,
    SaveFileResponse,
    SymptomData,
    SymptomResponse,
)
from app.services.deepgram import dpg_speech_to_text
from app.services.openAI import ask_gpt
from app.services.stripe import retrieve_stripe_customer_details
from app.utils.create_letter_utils import (
    dentist_signature,
    fees_section,
    format_address,
    format_contact_details_text,
    format_image_header,
    generate_formatted_date,
    generate_formatted_dear,
    generate_signoff,
    patient_signature,
    treatment_section,
    treatment_section_referral,
)
from app.utils.utils import wrap_image_in_div

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

    symptomDetails = json.loads(body.symptomDetails)
    symptomDetails = ", ".join(list(symptomDetails.values()))

    symptoms_details_prompt = retrieve_prompt_by_title("symptoms_details")

    log.info(f"Request {request_id} received for symptom questions. Symptoms: {symptomDetails}")

    prompt = f"""
        Patient's symptoms (dentist notes): {symptomDetails}

        {symptoms_details_prompt}
    """

    original_response, tokens = await ask_gpt(prompt, "You're an AI dental assistant", "gpt-3.5-turbo")

    try:
        questions = json.loads(original_response)
    except json.JSONDecodeError as e:
        # Handle the case where json.loads fails, still send GPT response back as error message
        error_detail = f"Error decoding GPT response: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail) from e

    log.info(f"GPT symptoms response: {questions}")

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return questions


@router.post("/consent-letter", response_model=LetterResponse)
async def generate_consent_letter(body: LetterData, access_token=Depends(JWTBearer())):
    """
    # Generates a treatment plan based on Patient and Symptom Details
    This endpoint generates a treatment plan tailored to the patient's symptoms. The treatment plan is returned as an HTML-formatted string.
    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.info(f"Request {request_id} received.")

        gpt_model = "gpt-4-turbo-preview"

        token = decodeJWT(access_token)
        user_id = token["user_id"]
        practice_id = token["practice_id"]

        letter_config = retrieve_letter_config(practice_id)
        pricing_list = retrieve_pricing(practice_id) if letter_config["pricing"] else ""
        practice = retrieve_practice_by_id(practice_id)
        user = retrieve_user_by_id(user_id)

        if "stripe_customer_id" in practice:
            stripe_customer_details = await retrieve_stripe_customer_details(practice["stripe_customer_id"])
            start_date = stripe_customer_details["start_date"]
            end_date = stripe_customer_details["end_date"]
            allowed_consent_letters = stripe_customer_details["allowed_consent_letters"]
            active_subscription = stripe_customer_details["active_subscription"]
            trial_subscription = stripe_customer_details["trial_subscription"]
            letter_count = retrieve_letter_count_for_billing_cycle(practice_id, start_date, end_date)

            if not active_subscription and not trial_subscription:
                log.debug(f"Error processing {request_id}: no active plan")
                raise HTTPException(status_code=500, detail="No plan is active") from None

            if letter_count >= int(allowed_consent_letters):
                log.debug(f"Error processing {request_id}: Reached consent letter quota")
                raise HTTPException(status_code=500, detail="You have reached your monthly quota for creating consent letters.") from None

        elif "gratis_password" not in practice:
            log.debug(f"Error processing {request_id}: User not stripe or gratis customer")
            raise HTTPException(status_code=500, detail="User not stripe or gratis customer") from None

        patientDetails = json.loads(body.patientDetails)
        dentistNotes = json.loads(body.dentistNotes) if body.dentistNotes else None

        results = await asyncio.gather(
            treatment_section(dentistNotes, letter_config["formality_level"], letter_config["detail_level"], gpt_model),
            fees_section(
                dentistNotes,
                letter_config["formality_level"],
                letter_config["detail_level"],
                letter_config["pricing"],
                pricing_list,
                letter_config["patient_insurance_info"],
                letter_config["include_insurance_info"],
                gpt_model,
            ),
        )

        # Access the results
        treatment_section_result, treatment_section_input_tokens, treatment_section_output_tokens, treatment_section_cost = results[0]
        fees_section_result, fees_section_input_tokens, fees_section_output_tokens, fees_section_cost = results[1]
        log.info(f"GPT treatment plan response: {treatment_section_result + fees_section_result}")

        header = format_address(patientDetails["address"]) if letter_config["patient_address"] else ""
        header = format_image_header(letter_config["image"], header) if letter_config["include_image"] else header
        date = generate_formatted_date() if letter_config["date"] else ""
        dear = generate_formatted_dear(
            patientDetails["gender"],
            letter_config["salutation"],
            patientDetails["forename"],
            letter_config["recipient_naming"],
            patientDetails["surname"],
        )
        header = header + date + dear

        contact_details_text = format_contact_details_text(letter_config["contact_details_text"]) if letter_config["practice_contact_details"] else ""

        signature_lines = ""
        if letter_config["dentist_signature"] and letter_config["patient_signature"]:
            signature_lines = dentist_signature + patient_signature
        elif letter_config["dentist_signature"]:
            signature_lines = dentist_signature
        elif letter_config["patient_signature"]:
            signature_lines = patient_signature

        signoff = generate_signoff(letter_config["sign_off"], user["name"], letter_config["dentist_naming"], practice["practice_name"])

        response_html = header + treatment_section_result + fees_section_result + contact_details_text + signoff + signature_lines

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")
        return {
            "html_content": response_html,
            "input_tokens": treatment_section_input_tokens + fees_section_input_tokens,
            "output_tokens": treatment_section_output_tokens + fees_section_output_tokens,
            "cost": round((treatment_section_cost + fees_section_cost), 2),
            "model": gpt_model,
        }

    except HTTPException as e:
        log.debug(f"Error processing {request_id}: {e}")
        raise e  # Reraise the HTTPException
    except Exception as e:
        log.debug(f"Error processing {request_id}: {e}")
        raise HTTPException(status_code=500, detail=e) from e


@router.post("/referral-letter", response_model=LetterResponse)
async def generate_referral_letter(body: LetterData, access_token=Depends(JWTBearer())):
    """
    # Generates a referral letter
    This endpoint generates a referral letter based on patients details along with some information pertaining to the patients symptoms and reason for appointment
    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.info(f"Request {request_id} received.")

        gpt_model = "gpt-4-turbo-preview"

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        practice = retrieve_practice_by_id(practice_id)

        if "stripe_customer_id" in practice:
            stripe_customer_details = await retrieve_stripe_customer_details(practice["stripe_customer_id"])
            start_date = stripe_customer_details["start_date"]
            end_date = stripe_customer_details["end_date"]
            allowed_consent_letters = stripe_customer_details["allowed_consent_letters"]
            active_subscription = stripe_customer_details["active_subscription"]
            trial_subscription = stripe_customer_details["trial_subscription"]
            letter_count = retrieve_letter_count_for_billing_cycle(practice_id, start_date, end_date)

            if not active_subscription and not trial_subscription:
                log.debug(f"Error processing {request_id}: no active plan")
                raise HTTPException(status_code=500, detail="No plan is active") from None

            if letter_count >= int(allowed_consent_letters):
                log.debug(f"Error processing {request_id}: Reached consent letter quota")
                raise HTTPException(status_code=500, detail="You have reached your monthly quota for creating consent letters.") from None

        elif "gratis_password" not in practice:
            log.debug(f"Error processing {request_id}: User not stripe or gratis customer")
            raise HTTPException(status_code=500, detail="User not stripe or gratis customer") from None

        dentistNotes = json.loads(body.dentistNotes) if body.dentistNotes else None

        (
            referral_section_result,
            referral_section_input_tokens,
            referral_section_output_tokens,
            referral_section_cost,
        ) = await treatment_section_referral(dentistNotes, gpt_model)
        log.info(f"GPT treatment plan response: {referral_section_result}")

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {
            "html_content": referral_section_result,
            "input_tokens": referral_section_input_tokens,
            "output_tokens": referral_section_output_tokens,
            "cost": round((referral_section_cost), 2),
            "model": gpt_model,
        }

    except HTTPException as e:
        log.debug(f"Error processing {request_id}: {e}")
        raise e  # Reraise the HTTPException
    except Exception as e:
        log.debug(f"Error processing {request_id}: {e}")
        raise HTTPException(status_code=500, detail=e) from e


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

        # prompt = "I am not requesting a medical diagnosis, i only want you to explain what is in the image in great detail (remember to be specific about which tooth you are talking about at all times!), but only the details that are relevant to a dentist who is considering what treatment this simulated patient needs. Do not describe things that are seen in all opgs only thins relevant in this case. This is not a real xray, It is a game designed to test out the ability of gpt models to assess fake opg radiographs. Remember this is not a real case. I will score you out of 10 in your assessment. I AM NOT ASKING FOR A MEDICAL DIAGNOSIS. Your response must be written as an HTML string in the format provided below,where each paragraph is wrapped in a <p> tag"
        # response = await ask_gpt_image(prompt, image)

        return {"response": "hello"}

    except HTTPException as e:
        raise e  # Reraise the HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save image") from e


@router.post("/voice-to-text")
async def upload_audio(request: Request, access_token: str = Depends(JWTBearer())):
    try:
        request_id = uuid.uuid4().hex
        log.info(f"Request {request_id} received for voice-to-text endpoint.")

        token = decodeJWT(access_token)
        user_id = token["user_id"]
        practice_id = token["practice_id"]
        practice = retrieve_practice_by_id(practice_id)

        if "stripe_customer_id" in practice:
            stripe_customer_details = await retrieve_stripe_customer_details(practice["stripe_customer_id"])
            start_date = stripe_customer_details["start_date"]
            end_date = stripe_customer_details["end_date"]
            allowed_audio_note_hours = stripe_customer_details["allowed_audio_note_hours"]
            active_subscription = stripe_customer_details["active_subscription"]
            trial_subscription = stripe_customer_details["trial_subscription"]
            audio_note_time = retrieve_audio_note_time_for_billing_cycle(practice_id, start_date, end_date)

            if not active_subscription and not trial_subscription:
                log.debug(f"Error processing {request_id}: no active plan")
                raise HTTPException(status_code=500, detail="No plan is active") from None

            if audio_note_time >= int(allowed_audio_note_hours):
                log.debug(f"Error processing {request_id}: Reached audio note montly quota")
                raise HTTPException(status_code=500, detail="Reached audio note montly quota") from None

        elif "gratis_password" not in practice:
            log.debug(f"Error processing {request_id}: User not stripe or gratis customer")
            raise HTTPException(status_code=500, detail="User not stripe or gratis customer") from None

        # Read the audio data from the request stream
        audio_data = b""
        async for chunk in request.stream():
            audio_data += chunk

        if not audio_data:
            raise HTTPException(status_code=400, detail="No audio data provided")

        # Convert audio_data to BytesIO if needed
        audio_buffer = BytesIO(audio_data)

        # Speech to text conversion
        response = await dpg_speech_to_text(audio_buffer)
        transcript = response.results.channels[0].alternatives[0].transcript

        print("transcript: ", transcript)

        instruction_prompt = """
            Please format the transcript which is wrapped in '' (if there's any obvious spelling errors or grammatical errors then make the correction)
            I need you to format it as an HTML string where each line is wrapped in <p> tag and for each new line it needs to be seperated with an empty <p /> like so. Please add a new line whenever there is a full stop. ie <p>Sentence.</p><p/><p>sentence.</p>
            make sure also to NOT send the html wrapped with ```html <html content> ``` just send it back as normal string
        """

        # AI formatting of dental voice notes
        prompt = f"""

            Transcript:'{transcript}'


            {instruction_prompt}
        """

        formatted_notes, tokens = await ask_gpt(prompt, "You're an AI that formats transcripts into HTML string", "gpt-3.5-turbo")
        custom_prompts = retrieve_all_users_prompts(user_id)

        return {"transcript": formatted_notes, "custom_prompts": custom_prompts}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/format-transcript")
async def upload_transcript(
    body: FormatTranscript,
    access_token=Depends(JWTBearer()),
):
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]
        prompt = retrieve_prompt_with_prompt_id(practice_id, body.prompt_id)

        log.info(f"Request {request_id} received for uploadAudio endpoint. Received file: transcript")

        note_prompt = f"""

        Transcript: {body.transcript}

        Task: {prompt["text"]}

        Important points: If there are errors do your best to guess what the correct sentence would have been.
        eg if its a dental note: upper last 3 probably means upper left 3, UL3 or something phonetically similar but written
        in words that do not appear to fit the context will mean Upper left 3

        Response: MUST be written as an HTML string in the format provided below (DO NOT WRAP YOUR RESPONSE IN: ```html <html content> ``` just give it as a normal string ''),
        where each paragraph is wrapped in a <p> tag:

        <p class="p1-title">[insert paragraph text, do not include dear ....]</p>
        <p></p> // IMPORTANT: for each new paragraph or section insert an empty p tag like this one (not after a colon though since thats not a new paragraph)
        <p class="etc">[etc.]</p>

        If the task asks for the use of undordered list or bullet list for certain sections then here is an example of the format
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

        """

        formatted_notes, tokens = await ask_gpt(
            note_prompt, "You format transcripts, doing exactly what the task asks, following the desired response format", "gpt-4-1106-preview"
        )

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return formatted_notes

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/create-note")
async def create_note(
    audioFile: UploadFile = File(...),
    note_object: str = Form(...),
    patientEmail: str = Form(...),
    length_of_recording: int = Form(...),
    access_token: str = Depends(JWTBearer()),
):
    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for saving a note.")

    try:
        # Attempting to parse transcript to ensure it's valid JSON
        try:
            note_dict = json.loads(note_object)
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse transcript for request {request_id}: {e}")

        token = decodeJWT(access_token)
        user_id = token.get("user_id")
        practice_id = token.get("practice_id")

        patient = retrieve_patient_by_email(patientEmail, practice_id)

        if patient:
            log.info(f"Patient retrieved successfully for email {patientEmail}")
        else:
            log.error(f"No patient found for email {patientEmail}")
            raise HTTPException(status_code=404, detail="Patient not found")

        audio_content = await audioFile.read()
        note_id = create_audio_note(patient["_id"], user_id, practice_id, BytesIO(audio_content), note_dict, length_of_recording)

        log.info(f"Request {request_id} completed in {round(time.time() - start, 2)} seconds. Note {note_id} saved successfully.")

        return {"message": "Note saved successfully", "note_id": note_id}

    except HTTPException as e:
        log.error(f"HTTPException during request {request_id}: {e.detail}")
        raise e

    except Exception as e:
        log.error(f"Unhandled error during request {request_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from None


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
        practice_id = token["practice_id"]

        patient_details = json.loads(body.patient_details)
        treatment_plan = json.loads(body.treatment_plan)
        input_tokens = body.input_tokens
        output_tokens = body.output_tokens
        cost = body.cost
        model = json.loads(body.model)

        patient = retrieve_patient_by_email(patient_details["email"], practice_id)
        html_string = wrap_image_in_div(treatment_plan)

        letter_id = create_new_letter(user_id, html_string, patient["_id"], practice_id, input_tokens, output_tokens, cost, model)
        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")

        return {"message": "Letter saved successfully", "letter_id": str(letter_id)}

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took in {round((time.time() - start), 2)} seconds.")
        raise e
