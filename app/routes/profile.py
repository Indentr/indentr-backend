from fastapi import APIRouter, Depends, Request

from app.middleware.jwt import JWTBearer

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/")
def get_profile(request: Request, access_token=Depends(JWTBearer())):
    return {}
