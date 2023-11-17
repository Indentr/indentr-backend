from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from app.middleware.jwt import JWTBearer, decodeJWT, signJWT
from app.models.login import UserLoginRequest, UserRegisterRequest

router = APIRouter(prefix="/auth", tags=["Authorisation"])


@router.post("/login")
def post_user_login(body: UserLoginRequest, request: Request):
    """
    This route handles user login requests. It expects a `UserLoginRequest` object
    as the request body, containing the user's email and password. The `check_user`
    function is invoked to validate the user's credentials against the database.
    If the user's credentials are valid, the `signJWT` function generates an access
    token, which is then returned in the response.
    """

    db = request.app.state.db
    users_collection = db["users"]
    user_document = users_collection.find_one({"email": body.email})

    if user_document and check_password_hash(user_document["password"], body.password):
        user_id = str(user_document["_id"])
        return signJWT(user_id)
    raise HTTPException(status_code=403, detail="Access denied.")


@router.post("/register")
def post_user_registration(body: UserRegisterRequest, request: Request):
    """
    This route handles user registration requests. It expects a `UserRegisterRequest`
    object as the request body, containing the user's name, email, and password.
    The route first checks if the provided email is already in use. If the email is
    available, it securely hashes the password and creates a new user in the database.
    """

    db = request.app.state.db
    users_collection = db["users"]
    configs_collection = db["configs"]

    # Check if user registrations are allowed
    configs_doc = configs_collection.find_one({})
    if not configs_doc or not configs_doc.get("allow_registrations", False):
        raise HTTPException(status_code=403, detail="User registrations are not allowed at the moment.")

    # Check if the email already exists
    existing_user = users_collection.find_one({"email": body.email})

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use")

    # If the email doesn't exist, hash the password and create the new user
    hash_pass = generate_password_hash(body.password, method="scrypt")
    users_collection.insert_one({"name": body.name, "email": body.email, "password": hash_pass})

    return {"message": "Registered successfully"}


@router.get("/user")
def authenticate_user(request: Request, access_token=Depends(JWTBearer())):
    """
    Checks if `access_token` is valid and then signs a new JWT based on the user_id
    """

    token = decodeJWT(access_token)
    user_id = token["user_id"]

    return signJWT(user_id)
