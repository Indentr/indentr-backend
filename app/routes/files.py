import logging
import time
import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.file import saveTreatmentPlan

router = APIRouter(prefix="/files", tags=["Files"])

log = logging.getLogger(__name__)

@router.get("/")
def get_files(request: Request, access_token=Depends(JWTBearer())):
    """
    Retrieves all users treatment plan.

    - **access_token**: JWT access token obtained during authentication.
    - **Response Model**: Dictionary with a single key "letters" containing a list of letter dictionaries.

    Each letter dictionary contains:
        - "_id": str (Letter's ID)
        - "patient_info": dict (Patient's information)
        - "consent_letter": str (Letter's content)
        - "user_id": str (User's ID)
        - "createdAt": str (Creation timestamp in format "YYYY-MM-DD HH:MM:SS")

    Returns:
        A dictionary with a single key "letters" containing a list of letter dictionaries.

    Raises:
        HTTPException 403: If authentication fails.
    """

    db = request.app.state.db
    token = decodeJWT(access_token)
    user_id = ObjectId(token['user_id'])

    letters_collection = db['letters']
    # Define projection to exclude user_id field
    projection = {
        'user_id': 0
    }

    # Sort the letters by patient_info.last_name
    sort_field = 'patient_info.last_name'
    # Find and retrieve the letters with projection and sorting
    letters = list(letters_collection.find({'user_id': user_id}, projection=projection).sort(sort_field))

    # Access the 'createdAt' field for each letter and convert it to time date format
    # Add a createdAt attribute to letter
    for letter in letters:
        created_at = letter['_id'].generation_time.strftime('%Y-%m-%d %H:%M:%S')
        letter['createdAt'] = created_at
        letter['_id'] = str(letter['_id'])

    return { "letters": letters }






@router.get("/{letter_id}/")
def get_treatment_plan(letter_id: str, request: Request, access_token=Depends(JWTBearer())):
    """
    """

    db = request.app.state.db
    letters_collection = db['letters']
    try:
        # Query the collection using the ObjectId
        letter = letters_collection.find_one({"_id": ObjectId(letter_id)})

        if letter is None:
            raise HTTPException(status_code=404, detail="Letter not found")

        created_at = letter['_id'].generation_time.strftime('%Y-%m-%d %H:%M:%S')
        letter['createdAt'] = created_at
        letter['_id'] = str(letter['_id'])
        letter['user_id'] = str(letter['user_id'])

        return letter

    except Exception:
         raise HTTPException(status_code=400, detail="Error getting treatment plan") from None




@router.post("/saveTreatmentPlan")
def save_treatment_plan(body: saveTreatmentPlan, request: Request, access_token=Depends(JWTBearer())):
    """
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for saving treatment plan.")

    letterId = body.letterId.strip('"\'')
    print(letterId)
    treatmentPlan = body.treatmentPlan
    db = request.app.state.db
    token = decodeJWT(access_token)
    token['user_id']
    letters_collection = db['letters']

    update_result = letters_collection.update_one(
        {"_id": ObjectId(letterId)},  # Find the document with the given _id
        {"$set": {"consent_letter": treatmentPlan}}  # Update the consent_letter field
    )

    if update_result.modified_count > 0:
        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return {"message": "Letter updated successfully"}
    else:
        log.debug(f"Request {request_id} failed and took {round((time.time() - start), 2)} seconds.")
        raise HTTPException(status_code=404, detail="Letter Id not found in database")




