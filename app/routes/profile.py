import json
import logging
import time
import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.encoders import jsonable_encoder

from app.database.crud import (
    create_new_user,
    delete_member,
    delete_price_list_crud,
    delete_service_from_price_list,
    retrieve_all_practice_users,
    retrieve_last_three_letters,
    retrieve_last_three_triage_requests,
    retrieve_practice_by_id,
    retrieve_practice_users_token_consumption,
    retrieve_price_list,
    retrieve_prompt_by_title,
    retrieve_user_by_email,
    retrieve_user_by_id,
    update_practice_details,
    update_price_list,
    update_user_details,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.user import (
    DeleteUser,
    EditPracticeField,
    EditUserField,
    UserRegistration,
)
from app.services.openAI import ask_gpt

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


@router.post("/uploadInitialPriceList")
async def upload_initial_price_list(price_list: str = Form(...), access_token=Depends(JWTBearer())):
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.info(f"Request {request_id} received for uploadInitialPriceLisst endpoint.")

        upload_price_list_prompt = retrieve_prompt_by_title("upload_price_list")
        
        # AI formatting of dental voice notes
        prompt = f"""

        Objective: Given the below price list, convert it into a json format:

        START OF PRICELIST

        {price_list}

        END OF PRICELIST

        {upload_price_list_prompt}

        """
        formatted_price_list_text, tokens = await ask_gpt(prompt, "You're an ai formatting dental price list", "gpt-3.5-turbo")

        try:
            formatted_price_list_json = json.loads(formatted_price_list_text)
        except json.JSONDecodeError as e:
            # Handle the case where json.loads fails, still send GPT response back as error message
            error_detail = f"Error decoding GPT response: {str(e)}"
            raise HTTPException(status_code=500, detail=error_detail) from e

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        # Convert ObjectId to string for JSON serialization
        return {
            "formatted_price_list_json": formatted_price_list_json,
        }

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/uploadPriceList")
async def upload_price_list(price_list_string: str = Form(...), access_token=Depends(JWTBearer())):
    try:
        start = time.time()
        request_id = uuid.uuid4().hex

        log.info(f"Request {request_id} received for uploadPriceLisst endpoint.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        try:
            # Attempt to call the update_price_list function
            update_price_list(price_list_string, practice_id)
        except Exception as e:
            # Handle exceptions that might be raised
            print(f"An error occurred: {e}")

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        # Convert ObjectId to string for JSON serialization
        return {
            "formatted_price_list_json": "success",
        }

    except HTTPException as e:
        raise e  # Reraise the HTTPException


# Helper function to convert ObjectId to string
def convert_objectid_to_str(item):
    if isinstance(item, dict):
        for key, value in item.items():
            if isinstance(value, ObjectId):
                item[key] = str(value)
            elif isinstance(value, list) or isinstance(value, dict):
                convert_objectid_to_str(value)
    elif isinstance(item, list):
        for entry in item:
            convert_objectid_to_str(entry)
    return item


@router.post("/getPriceList")
async def get_price_list(access_token=Depends(JWTBearer())):
    try:
        start = time.time()
        request_id = uuid.uuid4().hex
        log.info(f"Request {request_id} received for getPriceList endpoint.")

        token = decodeJWT(access_token)
        practice_id = token["practice_id"]

        try:
            # Attempt to retrieve the price list
            price_list_from_db = retrieve_price_list(practice_id)

            # Check if the price list is empty and handle accordingly
            if not price_list_from_db:
                log.info(f"No prices found for practice_id {practice_id}")
                price_list_from_db = []

            # Convert ObjectId to strings if price list is not empty
            else:
                price_list_from_db = convert_objectid_to_str(price_list_from_db)

        except Exception as e:
            log.error(f"An error occurred: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting price list: {str(e)}") from e

        log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

        return jsonable_encoder({"price_list_from_db": price_list_from_db})

    except HTTPException as e:
        raise e  # Reraise the HTTPException


@router.post("/deletePriceList")
async def delete_price_list(access_token=Depends(JWTBearer())):
    try:
        time.time()

        token = decodeJWT(access_token)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        practice_id = token["practice_id"]
        try:
            await delete_price_list_crud(practice_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting price list: {str(e)}") from e
        return {"message": "Price list deleted successfully"}

    except HTTPException as e:
        raise e


@router.post("/deleteSinglePrice")
async def delete_single_price(serviceName: str = Form(...), access_token=Depends(JWTBearer())):
    print("[Debug] delete_single_price called with serviceName:", serviceName)
    try:
        print("[Debug] Decoding JWT")
        token = decodeJWT(access_token)
        if token is None:
            print("[Debug] Token is None, raising 401")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        practice_id = token["practice_id"]
        print("[Debug] Practice ID:", practice_id)

        try:
            print("[Debug] Attempting to delete service from price list")
            delete_service_from_price_list(practice_id, serviceName)
            print("[Debug] Service deletion successful")
        except Exception as e:
            print("[Debug] Error occurred in delete_service_from_price_list:", str(e))
            raise HTTPException(status_code=500, detail=f"Error deleting service: {str(e)}") from e

        print("[Debug] Returning success message")
        return {"message": "Service deleted successfully"}

    except HTTPException as e:
        print("[Debug] HTTPException caught:", str(e))
        raise e


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
    Retrieves the user's profile information along with their latest letters.
    """
    try:
        token = decodeJWT(access_token)
        token["user_id"]
        practice_id = token["practice_id"]
        practice_users_token_consumption = retrieve_practice_users_token_consumption(practice_id)

        return {"tokens_consumed": practice_users_token_consumption}

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
        website = body.text if body.record == "website" else None

        # Update the user's details in MongoDB
        update_practice_details(practice_id, name, email, address, website)
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
