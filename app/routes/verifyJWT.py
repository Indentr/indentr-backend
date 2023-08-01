from fastapi import APIRouter, Depends

from app.middleware.jwt import JWTBearer

router = APIRouter(prefix="/verifyJWT", tags=["verifyJWT"])


@router.get("/")
def verifyJWT(access_token=Depends(JWTBearer())):
    """
    Verify the given access token.

    This route is protected by the `JWTBearer` dependency, which checks the validity of the access token.
    If the access token is valid, the `decodeJWT` function is used to decode and verify the token.
    If the access token is not valid, the endpoint will return a 403 error message.

    Parameters:
    - access_token (str, optional): The access token to be verified. This token is obtained from the `Authorization` header with the "Bearer" scheme.

    Returns:
    None
    """

    return None
