import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.database.crud import (
    create_new_user,
    delete_member,
    retrieve_all_practice_members,
    retrieve_last_three_letters,
    retrieve_last_three_triage_requests,
    retrieve_practice_by_id,
    retrieve_practice_users_token_consumption,
    retrieve_user_by_email,
    retrieve_user_by_id,
    update_user_details,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.user import DeleteUser, UserDetails, UserRegistration

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
        user = retrieve_user_by_id(user_id)

        return {"user": user}

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

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return {"letters": letters, "triage_requests": triage_requests}

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
        user = retrieve_user_by_id(user_id)
        practice_members = retrieve_all_practice_members(user["practice_id"])
        practice = retrieve_practice_by_id(user["practice_id"])

        return {"user": user, "practice_members": practice_members, "practice": practice}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.get("/billing")
def get_account_settings_billing(access_token=Depends(JWTBearer())):
    """
    Retrieves the user's profile information along with their latest letters.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        user = retrieve_user_by_id(user_id)
        practice_users_token_consumption = retrieve_practice_users_token_consumption(user["practice_id"])

        return {"tokens_consumed": practice_users_token_consumption}

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/saveDetails")
async def save_details(body: UserDetails, access_token=Depends(JWTBearer())):
    """
    Saves the user's email, phone number, and address to the database.
    """

    try:
        email = body.email
        phone = body.phone
        address = body.address

        if not email or not phone or not address:
            raise HTTPException(status_code=400, detail="No data provided")

        # Extract user's email from JWT token
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        # Update the user's details in MongoDB
        user = update_user_details(user_id, email, phone, address)
        return {"email": user["email"], "phone": user["phone"], "address": user["address"]}

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
def delete_member_account(body: DeleteUser, access_token=Depends(JWTBearer())):
    """
    This route handles when an account owner wants to delete a sub account from their practice
    """

    try:
        # Check if the email already exists and registrations are turned on
        delete_member(body.member_id, body.practice_id)

        return {"message": "Member deleted successfully"}

    except HTTPException as e:
        raise e
