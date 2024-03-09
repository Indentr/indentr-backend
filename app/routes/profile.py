import json
import logging
import time
import uuid
from calendar import monthrange
from datetime import datetime

import stripe
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.constants import STRIPE_SECRET_KEY
from app.database.crud import (
    create_new_user,
    delete_member,
    retrieve_all_practice_users,
    retrieve_audio_note_time_for_billing_cycle,
    retrieve_last_three_letters,
    retrieve_last_three_notes,
    retrieve_last_three_triage_requests,
    retrieve_letter_config,
    retrieve_letter_count_for_billing_cycle,
    retrieve_practice_by_id,
    retrieve_price_list,
    retrieve_prompt_by_title,
    retrieve_user_by_email,
    retrieve_user_by_id,
    update_letter_config,
    update_letter_image,
    update_practice_details,
    update_price_list,
    update_user_details,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.profile import UpdateLetterConfig
from app.models.user import (
    DeleteUser,
    EditPracticeField,
    EditUserField,
    UserRegistration,
)
from app.services.openAI import ask_gpt

stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter(prefix="/profile", tags=["Profile"])

# initiates logger
log = logging.getLogger(__name__)


@router.get("/")
def get_profile(access_token=Depends(JWTBearer())):
    """
    Retrieves the user's profile information along with their latest letters.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        practice_id = token["practice_id"]
        user = retrieve_user_by_id(user_id)
        practice = retrieve_practice_by_id(practice_id)

        return {"user": user, "practice": practice}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.get("/last-three-notes")
def get_last_three_notes(access_token=Depends(JWTBearer())):
    """
    Gets the users last three notes
    """

    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.debug(f"Request {request_id} received for getting last 3 triage_requests and letters.")

        token = decodeJWT(access_token)
        user_id = token["user_id"]

        notes = retrieve_last_three_notes(user_id)
        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {"notes": notes}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.get("/overview")
def get_overview(access_token=Depends(JWTBearer())):
    """
    Retrieves the user's profile information along with their latest letters.
    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.debug(f"Request {request_id} received for getting last 3 triage_requests and letters.")

        token = decodeJWT(access_token)
        user_id = token["user_id"]

        letters = retrieve_last_three_letters(user_id)
        triage_requests = retrieve_last_three_triage_requests(user_id)
        notes = retrieve_last_three_notes(user_id)

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {"letters": letters, "triage_requests": triage_requests, "notes": notes}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.get("/settings")
def get_account_settings(access_token=Depends(JWTBearer())):
    """
    Retrieves the user's profile information along with their latest letters.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        practice_id = token["practice_id"]
        user = retrieve_user_by_id(user_id)
        practice_members = retrieve_all_practice_users(practice_id)
        practice = retrieve_practice_by_id(practice_id)

        return {"user": user, "practice_members": practice_members, "practice": practice}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.get("/billing")
def get_account_settings_billing(access_token=Depends(JWTBearer())):
    """
    Retrieves the user's billing details, this includes:
    - The plan they are on
    - The number of letters they have created this billing cycle
    - The number of hours/minutes of dental note recording they have done this billing cycle.
    """
    try:
        token = decodeJWT(access_token)
        practice_id = token["practice_id"]
        practice = retrieve_practice_by_id(practice_id)
        plan_name = "gratis"
        allowed_audio_note_hours = "999999"
        allowed_consent_letters = "999999"

        if "stripe_customer_id" not in practice:
            current_date = datetime.now().date()
            start_date = datetime(current_date.year, current_date.month, 1)
            end_date = datetime(current_date.year, current_date.month, monthrange(current_date.year, current_date.month)[1])

        else:
            customer = stripe.Customer.retrieve(practice["stripe_customer_id"], expand=["subscriptions.data"])

            # get the active subscription and plan details
            subscriptions = customer.subscriptions.data
            active_subscription = next((sub for sub in subscriptions if sub.status == "active"), None)
            plan = active_subscription.plan if active_subscription else None
            plan_name = plan.metadata.nickname
            allowed_audio_note_hours = plan.metadata.allowed_audio_note_hours
            allowed_consent_letters = plan.metadata.allowed_consent_letters

            # retrieve the number of letters created in the current billing cycle
            start_date = datetime.fromtimestamp(active_subscription.current_period_start) if active_subscription else None
            end_date = datetime.fromtimestamp(active_subscription.current_period_end) if active_subscription else None

        letter_count = retrieve_letter_count_for_billing_cycle(practice_id, start_date, end_date)

        audio_note_time = retrieve_audio_note_time_for_billing_cycle(practice_id, start_date, end_date)

        return {
            "plan_name": plan_name,
            "allowed_consent_letters": allowed_consent_letters,
            "allowed_audio_note_hours": allowed_audio_note_hours,
            "letter_count": letter_count,
            "audio_note_time": audio_note_time,
            "start_date": start_date,
            "end_date": end_date,
        }

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/edit-user-field")
async def edit_user_field(body: EditUserField, access_token=Depends(JWTBearer())):
    """
    Edits the users name or email or password depending on what gets sent in the body.
    """

    try:
        # Extract user's email from JWT token
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        name = body.text if body.record == "name" else None
        email = body.text if body.record == "email" else None
        password = body.text if body.record == "password" else None

        # Update the user's details in MongoDB
        update_user_details(user_id, name, email, password)
        return {"message": "Edit successful"}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/edit-practice-field")
async def edit_practice_field(body: EditPracticeField, access_token=Depends(JWTBearer())):
    """
    Edits the users name or email or password depending on what gets sent in the body.
    """

    try:
        # Extract user's email from JWT token
        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        name = body.text if body.record == "name" else None
        email = body.text if body.record == "email" else None
        address = body.text if body.record == "address" else None
        phone = body.text if body.record == "phone" else None

        # Update the user's details in MongoDB
        update_practice_details(practice_id, name, email, address, phone)
        return {"message": "Edit successful"}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/register")
def create_new_account(body: UserRegistration, access_token=Depends(JWTBearer())):
    """
    This route handles user registration once a user is already authenticated.
    The route first checks if the provided email is already in use. If the email is
    available, it securely hashes the password and creates a new user in the database.
    """

    try:
        # Check if the email already exists and registrations are turned on
        try:
            # Attempt to retrieve the user by email
            existing_user = retrieve_user_by_email(body.email)
        except HTTPException as e:
            # Handle the 404 exception if user is not found
            if e.status_code == 404:
                existing_user = None
            else:
                raise

        # Check if the email already exists
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")

        new_user = create_new_user(body.name, body.email, body.password, body.practice_id, "Member")

        return {"new_user": new_user, "message": "Registered successfully"}

    except HTTPException as e:
        raise e


@router.post("/delete")
def deletes_member_account(body: DeleteUser, access_token=Depends(JWTBearer())):
    """
    This route handles when an account owner wants to delete a sub account from their practice
    """

    try:
        # Check if the email already exists and registrations are turned on
        delete_member(body.member_id, body.practice_id)

        return {"message": "Member deleted successfully"}

    except HTTPException as e:
        raise e


@router.get("/get-letter-config")
async def gets_letter_config(access_token=Depends(JWTBearer())):
    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.info(f"Request {request_id} received for get-letter-config endpoint.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        letter_config = retrieve_letter_config(practice_id)
        price_list = retrieve_price_list(practice_id)

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {"letter_config": letter_config, "price_list": price_list}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/update-letter-config")
async def updates_letter_config(body: UpdateLetterConfig, access_token=Depends(JWTBearer())):
    """
    This endpoint updates a practice's letter config document in mongo.
    """
    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.info(f"Request {request_id} received for update-letter-config endpoint.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        update_letter_config(
            practice_id,
            body.include_image,
            body.patient_address,
            body.date,
            body.salutation,
            body.recipient_naming,
            body.pricing,
            body.include_insurance_info,
            body.patient_insurance_info,
            body.patient_signature,
            body.dentist_signature,
            body.practice_contact_details,
            body.contact_details_text,
            body.sign_off,
            body.dentist_naming,
        )

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {"message": "Letter configuration saved"}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/save-letter-image/")
async def saveImg(file: UploadFile = File(...), access_token=Depends(JWTBearer())):
    """
    This endpoint allows a user to upload and save their profile image. The image data is received
    as binary data in the request stream. The image is then associated with the user's email and
    stored in the database.
    """

    try:
        # Get the image data from the request stream
        image_data = await file.read()

        if not image_data:
            raise HTTPException(status_code=400, detail="No image data provided")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        update_letter_image(practice_id, image_data)

        return {"message": "Image saved successfully!"}
    except Exception as e:
        raise e  # Reraise the HTTPException


@router.post("/format-price-list")
async def format_price_list(price_list: str = Form(...), access_token=Depends(JWTBearer())):
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.info(f"Request {request_id} received for uploadInitialPriceLisst endpoint.")

        upload_price_list_prompt = retrieve_prompt_by_title("upload_price_list")

        # AI formatting of dental voice notes
        prompt = f"""
            START OF PRICELIST
            {price_list}
            END OF PRICELIST

            {upload_price_list_prompt}
        """
        formatted_price_list_text, tokens = await ask_gpt(prompt, "You're an ai formatting dental price list", "gpt-3.5-turbo")

        try:
            formatted_price_list = json.loads(formatted_price_list_text)
        except json.JSONDecodeError as e:
            # Handle the case where json.loads fails, still send GPT response back as error message
            error_detail = f"Error decoding GPT response: {str(e)}"
            raise HTTPException(status_code=500, detail=error_detail) from e

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {
            "formatted_price_list": formatted_price_list,
        }

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/save-price-list")
async def save_price_list(price_list_string: str = Form(...), access_token=Depends(JWTBearer())):
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.info(f"Request {request_id} received for saving-price-list endpoint.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]
        price_list = json.loads(price_list_string)

        update_price_list(price_list, practice_id)

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {
            "message": "Prices were saved successfully!",
        }

    except HTTPException as e:
        raise e  # Reraise the HTTPException
