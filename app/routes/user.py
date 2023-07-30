from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException

from app.models.user import UserLoginRequest
# from app.middlewares.jwt import signJWT, JWTBearer
from app.services.user import check_user

router = APIRouter(prefix="/login", tags=["Login"])


# @router.get("/login-status")
# def get_user(auth=Depends(JWTBearer())):
#     return {
#         "status": True,
#     }


@router.post("/")
def post_user_login(body: UserLoginRequest, request: Request):
    db = request.app.state.db
    if check_user(email=body.email, password=body.password, db=db):
        return signJWT(body.email)
    raise HTTPException(status_code=403, detail="Access denied.")