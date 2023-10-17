from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException

from app.middleware.jwt import signJWT
from app.models.login import UserLoginRequest, UserRegisterRequest
from werkzeug.security import check_password_hash, generate_password_hash

router = APIRouter(prefix="/auth", tags=["Authorisation"])


@router.post("/login")
def post_user_login(body: UserLoginRequest, request: Request):
    """
    # Process User Login Request
    This route handles user login requests. It expects a `UserLoginRequest` object as the request body, containing the user's email and password. The `check_user` function is invoked to validate the user's credentials against the database.
    If the user's credentials are valid, the `signJWT` function generates an access token, which is then returned in the response.

    ## Parameters
    - `body` (UserLoginRequest): The request body containing the user's email and password.

    ## Response
    A dictionary containing the generated access token.

    ## Errors
    - **HTTPException**: If the user's credentials are invalid or if access is denied for any reason.

    """

    db = request.app.state.db
    users_collection = db['users']
    user_document = users_collection.find_one({'email': body.email})

    if user_document and check_password_hash(user_document["password"], body.password):
        user_id = str(user_document['_id'])
        return signJWT(user_id)
    raise HTTPException(status_code=403, detail="Access denied.")




@router.post("/register")
def post_user_registration(body: UserRegisterRequest, request: Request):
    """
        
    """

    db = request.app.state.db
    users_collection = db['users']

    print(body)

    # Check if the email already exists
    existing_user = users_collection.find_one({"email": body.email})

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use")

    # If the email doesn't exist, hash the password and create the new user
    hash_pass = generate_password_hash(body.password, method='sha256')
    users_collection.insert_one({'name': body.name, 'email': body.email, 'password': hash_pass})

    return {"message": "Registered successfully"}
