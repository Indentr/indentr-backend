import time
from typing import Dict

import jwt
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.constants import JWT_ALGORITHM, SECRET_KEY


def token_response(token: str):
    return {"access_token": token}


def signJWT(user_id: str, practice_id: str) -> Dict[str, str]:
    payload = {
        "user_id": user_id, 
        "practice_id": practice_id,
        "expires": time.time() + (3600 * 24),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

    return token_response(token)


def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=JWT_ALGORITHM)
        if decoded_token["expires"] < time.time():
            raise jwt.ExpiredSignatureError("Token has expired")

        return decoded_token

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if not self.verify_jwt(credentials.credentials):
            raise HTTPException(status_code=403, detail="Invalid token or expired token.")
        return credentials.credentials

    def verify_jwt(self, jwt: str) -> bool:
        isTokenValid: bool = False
        payload = None

        payload = decodeJWT(jwt)
        if payload:
            isTokenValid = True
        return isTokenValid
