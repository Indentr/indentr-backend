from fastapi import APIRouter, Request
from fastapi.exceptions import HTTPException

from app.middleware.jwt import signJWT
from app.models.user import UserLoginRequest
from app.services.user import check_user

router = APIRouter(prefix="/login", tags=["Login"])


@router.post("/")
def post_user_login(body: UserLoginRequest, request: Request):
    """
    Process user login request.

    This route is used to handle user login requests. It receives a `UserLoginRequest` object as the request body,
    containing the user's email and password. The `check_user` function is called to validate the user's credentials
    against the database.

    If the user's credentials are valid, the `signJWT` function is called to generate an access token, which is returned
    as the response.

    Parameters:
    - body (UserLoginRequest): The request body containing the user's email and password.

    Returns:
    dict: A dictionary containing the generated access token.

    Raises:
    HTTPException: If the user's credentials are invalid or if access is denied for any reason.
    """

    db = request.app.state.db
    if check_user(email=body.email, password=body.password, db=db):
        return signJWT(body.email)
    raise HTTPException(status_code=403, detail="Access denied.")
