import json
import logging
import time
import uuid
from email.mime.text import MIMEText

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.constants import DB_URI, TRIAGE_MAIL, TRIAGE_MAIL_PASSWORD
from app.database.atlas_search import atlas_search
from app.database.crud.patient import (
    create_new_patient,
    retrieve_patient_by_email,
    retrieve_patient_by_id,
    update_patients_practice_id,
)
from app.database.crud.practice import (
    retrieve_practice_by_id,
)
from app.database.crud.triage import (
    create_triage_request,
    delete_triage_requests,
    retrieve_all_triage_requests,
    retrieve_all_triage_requests_by_folder,
    retrieve_triage_request,
    update_triage_requests_folder,
    update_triage_requests_opened,
)
from app.database.crud.triage_settings import retrieve_triage_settings
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.triage import (
    AddPatientToPractice,
    CheckEmail,
    CreatePatientRequest,
    DeleteTriageRequests,
    DemoRequest,
    GenerateQuestions,
    SearchTriageRequests,
    ToggleTriageFolderRequest,
    ToggleTriageOpenedRequest,
)
from app.services.email import generate_patient_mail, generate_practice_mail, send_email
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
        triage_settings = retrieve_triage_settings(practice_id)

        return triage_settings

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/check-patient-by-email")
async def check_patient_by_email(body: CheckEmail):
    """
    Searches the practice's list of patients for a match.
    Returns true if a match is found.
    """
    start = time.time()

    try:
        email = body.email
        practice_id = body.practiceId
        result = False

        try:
            retrieve_patient_by_email(email, practice_id)
            result = True

        except HTTPException:
            try:
                retrieve_patient_by_email(email, None)
                result = True

            except HTTPException:
                result = False

        log.debug(f"Request  completed successfully in {round((time.time() - start), 2)} seconds.")

        return {"result": result}

    except HTTPException as e:
        log.debug(f"Request  failed and took {round((time.time() - start), 2)} seconds.")
        raise e


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
            patient = retrieve_patient_by_email(patient_details["email"], practice_id)
            if "practice_id" not in patient or patient["practice_id"] != practice_id:
                raise HTTPException(status_code=404, detail="Email not associated with practice")

        except HTTPException:
            try:
                patient = retrieve_patient_by_email(patient_details["email"], None)

            except HTTPException as e:
                raise HTTPException(status_code=404, detail="Email not associated with practice") from e

    else:
        # check if email exists within the whole system
        try:
            patient = retrieve_patient_by_email(patient_details["email"], None)

        except HTTPException:
            create_new_patient(
                forename=patient_details["forename"],
                surname=patient_details["surname"],
                email=patient_details["email"],
                dob=patient_details["dob"],
                gender=patient_details["gender"],
                address=patient_details["address"],
                practice_id=practice_id,
                phone_number=patient_details["phone"],
            )

    log.info(f"Request {request_id} received for triage symptom questions.")

    prompt = f"""
        Patients reason for appointment request: {patient_details["appointment_reason"]}

        I want you to ask the patient follow up questions relating to the patients reason for appointment.
        The aim of the follow up questions is to try and extract as much useful information from the patient as possible, so this way when the dentist sees the appointment request they have all the necessary information in terms of severity of the problem and patient's condition etc.

        Please ask the patient between 1 - 4 follow up questions, as many as you deem appropriate to get the info required. they may be open ended or closed as you see fit.
        If the reason for appointment doesn't necessitate any follow up questions or their reason for appointment doesn't pertain to dentistry then just send back and empty array as your response.

        Please format your response as a JSON string, similar to what's shown below (choose between 1-4 q's depending on the appointment reason, if appointment reason is not severe ask less questions, if its more severe ask more questions):
        [
            {{
                "symptom": "General check-up",
                "q1": "When was your last check-up?"
            }},
        ]
        another example this time with more questions being asked
        [
            {{
                "symptom": "[Symptom name]",
                "q1": "[Insert q1]",
                "q2": "[q2]",
                "q3": "[q3]"
            }},
        ]

        If you think the reason for appointment doesn't have enough information then ask more questions, but if the reason for appointment is clear then ask less questions.
        IMPORTANT: Your response must be a string!!!!, DO NOT wrap the response like so  ```json ```!!!!
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

    return {"questions": questions, "appointment_reason": patient_details["appointment_reason"]}


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
        The patient's stated reason for appointment: {body.appointment_reason}
        The questions and patients answers: {symptom_details}

        A patient has just filled out a dental triage form where they were asked some questions based on a dental symptom they have.

        Based on the patients patients response I need you to give a response to the following questions:
        1. A diagnosis title, a very short title of like 5 words max based on the appointment request
        2. A detailed overview of the problem, a dentist will be reading this so you don't have to explain what anything means. If the diagnosis is unclear then say so.
        3. A severity score out of 10 (10 being absolutely must see a dentist in the next hour or they will die, 1 being general checkup).
        4. A brief overview of instructions for the patient while they wait for their appointment. This will be displayed to the patient. If the symptom is mild then it should say how to manage it in the menatime, if the symptom is very severe then it should tell them to call the practice.

        Your responses to the following must be formatted as JSON, as shown below:
        {{
            "diagnosis": "[Your diagnosis title],
            "overview": "[A general overview of the problem]",
            "severity": "[An integer value between 0/10]",
            "instructions": "[Instructions on what the patient can do while they wait for their appointment to be scheduled (don't tell them to schedule an appointment since that's what they've just done)]":
        }}

        Do not wrap the response in  ```json <response> ```

    """

    original_response, tokens = await ask_gpt(prompt, "You're an AI dental assistant", "gpt-3.5-turbo")

    try:
        response = json.loads(original_response)

    except json.JSONDecodeError as e:
        # Handle the case where json.loads fails, still send GPT response back as error message
        error_detail = f"Error decoding GPT response: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail) from e

    requested_date = None if not patient_details["requested_date"] else patient_details["requested_date"]

    appointment_reason = patient_details["appointment_reason"]

    if not patient_details["forename"]:
        patient_details = retrieve_patient_by_email(patient_details["email"], practice_id)

    create_triage_request(
        practice_id=practice_id,
        email=patient_details["email"],
        phone=patient_details["phone"],
        diagnosis=response["diagnosis"],
        reason_for_request=appointment_reason,
        overview=response["overview"],
        severity=response["severity"],
        requested_date=requested_date,
        GPT_QA=symptom_details,
        patient_instruction=response["instructions"],
    )

    practice = retrieve_practice_by_id(practice_id)

    if "triage_email" not in practice:
        practice["triage_email"] = practice["primary_email"]

    triage_settings = retrieve_triage_settings(practice["_id"])

    practice_mail_text = generate_practice_mail(patient_details, response["diagnosis"], appointment_reason, triage_settings["primary_color"])

    send_email("New triage request", practice_mail_text, TRIAGE_MAIL, practice["triage_email"], TRIAGE_MAIL_PASSWORD)

    patient_mail_text = generate_patient_mail(practice, patient_details, response["instructions"], triage_settings["primary_color"])

    send_email("Appointment request sent", patient_mail_text, TRIAGE_MAIL, patient_details["email"], TRIAGE_MAIL_PASSWORD)

    return {"success": True, "instructions": response["instructions"]}


@router.get("/get-requests/{folder}")
async def get_all_triage_requests(folder: str, access_token=Depends(JWTBearer())):
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

    triage_requests = []
    if folder == "all":
        triage_requests = retrieve_all_triage_requests(practice_id)
    else:
        triage_requests = retrieve_all_triage_requests_by_folder(practice_id, folder)

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

    return triage_request


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


@router.post("/toggle-folder-status/")
async def toggle_triage_request_folder_status(body: ToggleTriageFolderRequest, access_token=Depends(JWTBearer())):
    """
    # Changes selected triage requests to be folder status (e.g. ongoing or completed)
    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.debug(f"Request {request_id} received for changing selected triage requests folder status to be {body.folder}.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        triage_requests = json.loads(body.selected_requests)
        folder = body.folder

        update_triage_requests_folder(triage_requests, folder, practice_id)

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {"success": True}

    except HTTPException as e:
        raise e


@router.post("/search-requests/")
async def search_triage_requests(body: SearchTriageRequests, access_token=Depends(JWTBearer())):
    """
    # searches triage requests

    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.debug(f"Request {request_id} received for toggling triage requests to be opened/closed.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        search_param = body.search_param

        table = "triage_responses"
        returned_fields = {
            "_id": 1,
            "patient_id": 1,
            "diagnosis": 1,
            "general_overview": 1,
            "severity": 1,
            "opened": 1,
            "created_at": 1,
            "folder": 1,
        }
        pipeline = [
            {
                "$search": {
                    "index": "default",
                    "compound": {
                        "should": [
                            {"autocomplete": {"query": search_param, "path": "diagnosis"}},
                            {"autocomplete": {"query": search_param, "path": "patient_details.forename"}},
                            {"autocomplete": {"query": search_param, "path": "patient_details.surname"}},
                        ],
                        "filter": [
                            {"equals": {"value": ObjectId(practice_id), "path": "practice_id"}},
                        ],
                        "minimumShouldMatch": 1,
                    },
                }
            },
            {"$limit": 25},
            {"$project": returned_fields},
        ]

        result = atlas_search(DB_URI, table, pipeline)
        for i in result:
            i["_id"] = str(i["_id"])
            if "patient_id" in i:
                patient_details = retrieve_patient_by_id(str(i["patient_id"]), practice_id)
                del patient_details["dob"]
                del patient_details["gender"]
                del patient_details["address"]
                del patient_details["email"]
                del i["patient_id"]
                i["patient_details"] = patient_details

            if "createdAt" in i:
                i["createdAt"] = i["createdAt"].strftime("%Y-%m-%d %H:%M:%S")

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return result

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


@router.post("/submit-details")
async def submit_details(body: DemoRequest):
    try:
        # Parse the user details from the request body
        user_details = json.loads(body.user_details)

        # Extract user information from the parsed details
        full_name = user_details.get("name", "")
        email = user_details.get("email", "")
        phone = user_details.get("phone", "")
        message = user_details.get("message", "")

        # Use only the first name by splitting the full name
        first_name = full_name.split()[0] if full_name else "there"

        # Construct the indentr_mail_text with user details
        indentr_mail_text = (
            f"New Demo Request Received:\n\n"
            f"Name: {full_name}\n"
            f"Email: {email}\n"
            f"Phone: {phone}\n"
            f"Message: {message}\n\n"
            f"Please reach out to {first_name} to set up a call."
        )

        # Convert the text message to a MIMEText object
        mime_text = MIMEText(indentr_mail_text, "plain")

        # Send the email
        send_email("New Demo Request", mime_text, TRIAGE_MAIL, "book-demo@indentr.com", TRIAGE_MAIL_PASSWORD)

        # Return a friendly response message
        response_message = (
            f"Thank you, {first_name}! "
            f"We have received your request and will be in touch shortly to set up a call with one of our team members. "
            f"Please look out for an email at {email} or a phone call at {phone}. "
            "Have a wonderful day!"
        )

        return {"success": True, "message": response_message}
    except HTTPException as e:
        raise e
