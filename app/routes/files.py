import json
import logging
import time
import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.constants import DB_URI
from app.database.atlas_search import atlas_search
from app.database.crud.audio_note import (
    delete_note,
    retrieve_all_users_notes,
    retrieve_all_users_notes_filtered_by_char,
    retrieve_note,
    retrieve_note_audio,
    retrieve_notes_alphabet_status,
    retrieve_patients_last_three_notes,
    update_note,
)
from app.database.crud.custom_prompt import retrieve_all_users_prompts
from app.database.crud.letter import (
    delete_letter,
    retrieve_all_users_letters,
    retrieve_all_users_letters_filtered_by_char,
    retrieve_letters_alphabet_status,
    retrieve_patients_last_three_letters,
    retrieve_user_letter,
    update_letter,
)
from app.database.crud.patient import (
    delete_patient,
    retrieve_all_patients_by_practice,
    retrieve_all_practices_patients_filtered_by_char,
    retrieve_patient_by_email,
    retrieve_patient_by_id,
    retrieve_patients_alphabet_status,
)
from app.middleware.jwt import JWTBearer, decodeJWT
from app.models.file import DeleteFile, GetFile, SaveFile, SearchFiles, SelectChar
from app.utils.utils import wrap_image_in_div

router = APIRouter(prefix="/files", tags=["Files"])

log = logging.getLogger(__name__)


@router.post("/get-files/")
def get_files(body: GetFile, access_token=Depends(JWTBearer())):
    """
    # Gets all files
    Gets all notes/consent letters based on the file_type that gets passed in.
    """

    start = time.time()
    request_id = uuid.uuid4().hex

    log.info(f"Request {request_id} received for getting all users consent letters.")

    token = decodeJWT(access_token)
    user_id = token["user_id"]
    practice_id = token["practice_id"]

    file_type = body.file_type

    if file_type == "letter":
        files = retrieve_all_users_letters(user_id=user_id) if body.created_by == "You" else retrieve_all_users_letters(practice_id=practice_id)

    elif file_type == "note":
        files = retrieve_all_users_notes(user_id=user_id) if body.created_by == "You" else retrieve_all_users_notes(practice_id=practice_id)

    elif file_type == "patient":
        files = retrieve_all_patients_by_practice(practice_id)

    log.debug(f"Request {request_id} completed in {round((time.time() - start), 2)} seconds.")

    return {"files": files}


@router.get("/{file_type}/{file_id}")
def get_file(file_type: str, file_id: str, access_token=Depends(JWTBearer())):
    """
    Retrieves a file based on the provided file ID.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        practice_id = token["practice_id"]
        letters = []
        notes = []
        file = ""
        patient_details = []
        custom_prompts = []

        if file_type == "letter":
            file = retrieve_user_letter(file_id, user_id)
        elif file_type == "note":
            file = retrieve_note(file_id, user_id)
            patient_details = retrieve_patient_by_email(file["patient_details"]["email"], practice_id)
            del patient_details["_id"]
            custom_prompts = retrieve_all_users_prompts(user_id)

        elif file_type == "patient":
            file = retrieve_patient_by_id(file_id, practice_id)
            letters = retrieve_patients_last_three_letters(file_id)
            notes = retrieve_patients_last_three_notes(file_id)

        return {"file": file, "patient_details": patient_details, "custom_prompts": custom_prompts, "letters": letters, "notes": notes}

    except HTTPException as e:
        raise e


@router.get("/get-audio-data/{note_id}/")
def get_audio_data(note_id: str, access_token=Depends(JWTBearer())):
    """
    Retrieves a note's audio based on the provided file ID.
    """
    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        audio_data = retrieve_note_audio(note_id, user_id)
        headers = {
            "Content-Disposition": 'attachment; filename="audio.webm',
            "Content-Type": "audio/webm",
        }
        return StreamingResponse(iter([audio_data]), headers=headers)

    except HTTPException as e:
        raise e


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
            html_string = wrap_image_in_div(json.loads(body.file_text))
            update_letter(body.file_id, html_string, user_id)
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
        practice_id = token["practice_id"]
        returned_fields = {}

        if body.file_type == "letter":
            table = "letters"
            path = "consent_letter"
            returned_fields = {
                "_id": 1,
                "patient_id": 1,
                "createdAt": 1,
                "consent_letter": 1,
            }
        if body.file_type == "note":
            table = "audio_note"
            path = "formatted_notes"
            returned_fields = {
                "_id": 1,
                "patient_id": 1,
                "createdAt": 1,
                "transcript": 1,
                "formatted_notes": 1,
            }

        if body.file_type == "letter" or body.file_type == "note":
            search_param = body.search_param
            filter_condition = None

            if body.created_by == "You":
                filter_condition = {"equals": {"value": ObjectId(user_id), "path": "user_id"}}
            else:
                filter_condition = {"equals": {"value": ObjectId(practice_id), "path": "practice_id"}}

            pipeline = [
                {
                    "$search": {
                        "index": "default",
                        "compound": {
                            "should": [
                                {"autocomplete": {"query": search_param, "path": path}},
                                {"autocomplete": {"query": search_param, "path": "patient_details.forename"}},
                                {"autocomplete": {"query": search_param, "path": "patient_details.surname"}},
                            ],
                            "filter": [filter_condition],
                            "minimumShouldMatch": 1,
                        },
                    }
                },
                {"$unwind": "$formatted_notes"},  # Unwind to work with each element individually
                {
                    "$lookup": {
                        "from": "custom_prompts",
                        "localField": "formatted_notes.note_prompt_id",
                        "foreignField": "_id",
                        "as": "custom_prompts",
                    }
                },
                {
                    "$addFields": {
                        "formatted_notes.title": {
                            "$arrayElemAt": [
                                {
                                    "$map": {
                                        "input": "$custom_prompts",
                                        "as": "cp",
                                        "in": {"$cond": [{"$eq": ["$$cp._id", "$formatted_notes.note_prompt_id"]}, "$$cp.title", None]},
                                    }
                                },
                                0,
                            ]
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$_id",
                        "patient_id": {"$first": "$patient_id"},
                        "user_id": {"$first": "$user_id"},
                        "practice_id": {"$first": "$practice_id"},
                        "audio": {"$first": "$audio"},
                        "transcript": {"$first": "$transcript"},
                        "createdAt": {"$first": "$createdAt"},
                        "patient_details": {"$first": "$patient_details"},
                        "length_of_recording": {"$first": "$length_of_recording"},
                        "formatted_notes": {"$push": "$formatted_notes"},  # Group back the formatted_notes
                    }
                },
                {"$sort": {"_id": -1}},
                {"$limit": 15},
                {"$project": returned_fields},
            ]

            if body.file_type == "letter":
                pipeline = [
                    {
                        "$search": {
                            "index": "default",
                            "compound": {
                                "should": [
                                    {"autocomplete": {"query": search_param, "path": path}},
                                    {"autocomplete": {"query": search_param, "path": "patient_details.forename"}},
                                    {"autocomplete": {"query": search_param, "path": "patient_details.surname"}},
                                ],
                                "filter": [filter_condition],
                                "minimumShouldMatch": 1,
                            },
                        }
                    },
                    {"$sort": {"_id": -1}},
                    {"$limit": 15},
                    {"$project": returned_fields},
                ]

        if body.file_type == "patient":
            search_param = body.search_param
            table = "patients"
            pipeline = [
                {
                    "$search": {
                        "index": "default",
                        "compound": {
                            "should": [
                                {"autocomplete": {"query": search_param, "path": "forename"}},
                                {"autocomplete": {"query": search_param, "path": "surname"}},
                                {"autocomplete": {"query": search_param, "path": "email"}},
                            ],
                            "filter": [
                                {"equals": {"value": ObjectId(practice_id), "path": "practice_id"}},
                            ],
                            "minimumShouldMatch": 1,
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "forename": 1,
                        "surname": 1,
                        "gender": 1,
                        "email": 1,
                        "dob": 1,
                        "address": 1,
                    }
                },
            ]

        result = atlas_search(DB_URI, table, pipeline)

        for i in result:
            i["_id"] = str(i["_id"])
            if body.file_type == "note":
                formatted_notes = []
                if "formatted_notes" in i and i["formatted_notes"]:
                    for formatted_note in i.get("formatted_notes", []):
                        if isinstance(formatted_note, dict):
                            formatted_notes.append(
                                {
                                    "note_prompt_id": str(formatted_note["note_prompt_id"]),  # Convert ObjectId to string
                                    "note_text": formatted_note["note_text"],
                                    "title": formatted_note["title"],
                                }
                            )
                    i["formatted_notes"] = formatted_notes

            if "patient_id" in i:
                patient_details = retrieve_patient_by_id(str(i["patient_id"]), practice_id)
                del patient_details["dob"]
                del i["patient_id"]
                i["patient_details"] = patient_details

            if "createdAt" in i:
                i["createdAt"] = i["createdAt"].strftime("%Y-%m-%d %H:%M:%S")

        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return result

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took in {round((time.time() - start), 2)} seconds.")
        log.debug(f"Request {request_id} Error: {e.detail}")
        raise e


@router.post("/init-alphabetised/")
def init_alphabetised(body: GetFile, access_token=Depends(JWTBearer())):
    """
    # Initialises alphabtised when user clicks on alphabet sort button on front end
    returns a dictionary of number of files for each letter in the alphabet.
    also returns all files that are present for the first letter in alphabet that is > 0
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for initialising alphabetised search.")

    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        practice_id = token["practice_id"]
        starts_with_char = None

        if body.file_type == "letter":
            alphabet_status = retrieve_letters_alphabet_status(user_id)
            starts_with_char = next((char for char, count in alphabet_status.items() if count > 0), None)

        elif body.file_type == "note":
            alphabet_status = retrieve_notes_alphabet_status(user_id)
            starts_with_char = next((char for char, count in alphabet_status.items() if count > 0), None)

        elif body.file_type == "patient":
            alphabet_status = retrieve_patients_alphabet_status(practice_id)
            starts_with_char = next((char for char, count in alphabet_status.items() if count > 0), None)

        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return {"starts_with_char": starts_with_char, "alphabet_status": alphabet_status}

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took {round((time.time() - start), 2)} seconds.")
        log.debug(f"Request {request_id} Error: {e.detail}")
        raise e


@router.post("/select-char/")
def select_char(body: SelectChar, access_token=Depends(JWTBearer())):
    """
    # Retrieves all files whose patients first name starts with 'char'
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for selecting a char in alphabetised search.")

    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        practice_id = token["practice_id"]
        files = None

        if body.file_type == "letter":
            files = (
                retrieve_all_users_letters_filtered_by_char(user_id=user_id, starts_with=body.char)
                if body.created_by == "You"
                else retrieve_all_users_letters_filtered_by_char(practice_id=practice_id, starts_with=body.char)
            )
        elif body.file_type == "note":
            files = (
                retrieve_all_users_notes_filtered_by_char(user_id=user_id, starts_with=body.char)
                if body.created_by == "You"
                else retrieve_all_users_notes_filtered_by_char(practice_id=practice_id, starts_with=body.char)
            )
        elif body.file_type == "patient":
            files = retrieve_all_practices_patients_filtered_by_char(practice_id, body.char)

        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return {"files": files}

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took {round((time.time() - start), 2)} seconds.")
        log.debug(f"Request {request_id} Error: {e.detail}")
        raise e


@router.post("/delete-file/")
def delete_file(body: DeleteFile, access_token=Depends(JWTBearer())):
    """
    # Deletes a file based on file_type and the file_id
    """

    start = time.time()
    request_id = uuid.uuid4().hex
    log.info(f"Request {request_id} received for deleting a file.")

    try:
        token = decodeJWT(access_token)
        user_id = token["user_id"]
        practice_id = token["practice_id"]

        if body.file_type == "letter":
            delete_letter(user_id, body.file_id)
        if body.file_type == "note":
            delete_note(practice_id, body.file_id)
        if body.file_type == "patient":
            delete_patient(practice_id, body.file_id)

        log.debug(f"Request {request_id} completed successfully in {round((time.time() - start), 2)} seconds.")
        return {"success": True}

    except HTTPException as e:
        log.debug(f"Request {request_id} failed and took {round((time.time() - start), 2)} seconds.")
        log.debug(f"Request {request_id} Error: {e.detail}")
        raise e
