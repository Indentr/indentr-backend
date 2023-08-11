import json

from fastapi import APIRouter, Depends, Request

from app.middleware.jwt import JWTBearer
from app.models.create import SymptomData

router = APIRouter(prefix="/create", tags=["Create"])



@router.post("/symptoms")
async def generateQuestions(body: SymptomData, request: Request, access_token=Depends(JWTBearer())):
    patientDetails = json.loads(body.patientDetails)
    print(patientDetails['forename'])

    return {  }
