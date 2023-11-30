from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from werkzeug.security import check_password_hash

from app.database.crud import (
    create_new_practice,
    create_new_user,
    retrieve_allow_user_registrations,
    retrieve_user_by_email,
)
from app.middleware.jwt import JWTBearer, decodeJWT, signJWT
from app.models.login import UserLoginRequest, UserRegisterRequest

router = APIRouter(prefix="/auth", tags=["Authorisation"])


@router.post("/login")
def post_user_login(body: UserLoginRequest):
    """
    This route handles user login requests. It expects a `UserLoginRequest` object
    as the request body, containing the user's email and password. The `check_user`
    function is invoked to validate the user's credentials against the database.
    If the user's credentials are valid, the `signJWT` function generates an access
    token, which is then returned in the response.
    """

    try:
        user_document = retrieve_user_by_email(body.email)

        if user_document and check_password_hash(user_document["password"], body.password):
            user_id = str(user_document["_id"])
            return signJWT(user_id)
        else:
            raise HTTPException(status_code=403, detail="Access denied")

    except HTTPException as e:
        raise e


@router.post("/register")
def post_user_registration(body: UserRegisterRequest):
    """
    This route handles user registration requests. It expects a `UserRegisterRequest`
    object as the request body, containing the user's name, email, and password.
    The route first checks if the provided email is already in use. If the email is
    available, it securely hashes the password and creates a new user in the database.
    """

    try:
        # Check if user registrations are turned on
        if not retrieve_allow_user_registrations():
            raise HTTPException(status_code=403, detail="User registrations are not allowed at the moment.")

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

        practice_id = create_new_practice(body.practice_name, body.practice_email, body.practice_url, body.address, body.phone)

        create_new_user(body.name, body.email, body.password, practice_id, "Owner")

        return {"message": "Registered successfully"}

    except HTTPException as e:
        raise e


@router.get("/user")
def authenticate_user(access_token=Depends(JWTBearer())):
    """
    Checks if `access_token` is valid and then signs a new JWT based on the user_id
    """

    token = decodeJWT(access_token)
    user_id = token["user_id"]

    return signJWT(user_id)
