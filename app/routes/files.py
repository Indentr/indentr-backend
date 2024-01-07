import json
import logging
import time
import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.constants import DB_URI
from app.database.atlas_search import atlas_search
from app.database.crud import (
    retrieve_all_users_letters,
    retrieve_all_users_notes,
    retrieve_note,
    retrieve_patient_by_id,
    retrieve_user_letter,
    update_letter,
    update_note,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.file import GetFiles, SaveFile, SearchFiles

router = APIRouter(prefix="/files", tags=["Files"])

log = logging.getLogger(__name__)


@router.post("/get-files/")
def get_files(body: GetFiles, access_token=Depends(JWTBearer())):
    """
    # Gets all letters
    This endpoint is called on files page load.
    """

    start = time.time()
    request_id = uuid.uuid4().hex

    log.info(f"Request {request_id} received for getting all users consent letters.")

    token = decodeJWT(access_token)
    user_id = token["user_id"]

    file_type = body.file_type

    if file_type == "letter":
        files = retrieve_all_users_letters(user_id)

    else:
        files = retrieve_all_users_notes(user_id)

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return {"files": files}


@router.get("/{file_id}")
def get_file(file_id: str, access_token=Depends(JWTBearer())):
    """
    Retrieves a treatment plan based on the provided letter ID.
    """

    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        try:
            file = retrieve_user_letter(file_id, user_id)
            file_type = "letter"
        except HTTPException:
            file = retrieve_note(file_id, user_id)
            file_type = "note"

        return {"file": file, "file_type": file_type}

    except HTTPException:
        raise HTTPException(status_code=400, detail="No file found") from None


@router.post("/save-file/")
def save_file(body: SaveFile, access_token=Depends(JWTBearer())):
    """
    Saves a file to the database. If a file with the provided ID
    exists, the necessary field will be updated with the new file text.
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for saving a file.")

    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]

        if body.file_type == "letter":
            update_letter(body.file_id, json.loads(body.file_text), user_id)
        else:
            update_note(body.file_id, json.loads(body.file_text), user_id)

        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return {"message": "File updated successfully"}

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took {round((time.time() - start), 2)} seconds.")
        log.debug(f"Request {request_id} Error: {e.detail}")
        raise e


@router.post("/search-files/")
def search_files(body: SearchFiles, access_token=Depends(JWTBearer())):
    """
    # Searches the database for a file based on file type and search param.
    Uses atlas search autocomplete to predict what file the user is most likely looking for.
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for searching for a file.")

    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        returned_fields = {}

        print("user_id: ", ObjectId(user_id))

        if body.file_type == "letter":
            table = "letters"
            path = "consent_letter"
            returned_fields = {
                "_id": 1,
                "patient_id": 1,
                "createdAt": 1,
                "consent_letter": 1,
            }
        else:
            table = "audio_note"
            path = "formatted_notes"
            returned_fields = {
                "_id": 1,
                "patient_id": 1,
                "createdAt": 1,
                "formatted_notes": 1,
            }

        search_param = body.search_param
        pipeline = [
            {
                "$search": {
                    "index": "default",
                    "compound": {
                        "should": [
                            {"autocomplete": {"query": search_param, "path": path}},
                        ],
                        "filter": [
                            {"equals": {"value": ObjectId(user_id), "path": "user_id"}},
                        ],
                        "minimumShouldMatch": 1,
                    },
                }
            },
            {"$limit": 15},
            {"$project": returned_fields},
        ]
        result = atlas_search(DB_URI, table, pipeline)
        for i in result:
            i["_id"] = str(i["_id"])
            patient_details = retrieve_patient_by_id(str(i["patient_id"]))
            del patient_details["dob"]
            del patient_details["gender"]
            del patient_details["address"]
            del patient_details["email"]
            del i["patient_id"]
            i["patient_details"] = patient_details
            i["createdAt"] = i["createdAt"].strftime("%Y-%m-%d %H:%M:%S")

        print(result)

        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return result

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took in {round((time.time() - start), 2)} seconds.")
        log.debug(f"Request {request_id} Error: {e.detail}")
        raise e
