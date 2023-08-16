from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException

from app.middleware.jwt import signJWT
from app.models.login import UserLoginRequest
from app.services.login import check_user

router = APIRouter(prefix="/login", tags=["Login"])


@router.post("/")
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

    if user_document and check_user(email=body.email, password=body.password, db=db):
        user_id = str(user_document['_id'])
        return signJWT(user_id)
    raise HTTPException(status_code=403, detail="Access denied.")
