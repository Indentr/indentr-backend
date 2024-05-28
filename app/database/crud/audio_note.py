# Audio note CRUD file
# -- Files must start with either create, retrieve, update, delete

from datetime import datetime
from io import BytesIO
from string import ascii_lowercase
from typing import Any, Dict

from bson import ObjectId
from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.audio_note import AudioNote, NotePromptOutputs
from app.database.schemas.patient import Patient, PatientName


def create_audio_note(
    patient_id: str,
    user_id: str,
    practice_id: str,
    audio_bytesio: BytesIO,
    note_dict: Dict[str, Any],
    length_of_recording: int,
) -> str:
    try:
        # Convert BytesIO to bytes
        audio_bytes = audio_bytesio.getvalue()

        # Fetch the patient object
        patient = Patient.objects.get(id=patient_id)

        patient_details = PatientName(forename=patient.forename, surname=patient.surname)

        formatted_notes = []
        for formatted_note in note_dict["formatted_notes"]:
            notePromptOutput = NotePromptOutputs(note_prompt_id=formatted_note["note_prompt_id"], note_text=formatted_note["note_text"])
            formatted_notes.append(notePromptOutput)

        audio_note = AudioNote(
            patient_id=patient_id,
            user_id=user_id,
            practice_id=practice_id,
            audio=audio_bytes,
            transcript=note_dict["transcript"],
            formatted_notes=formatted_notes,
            patient_details=patient_details,
            length_of_recording=length_of_recording,
            input_tokens=note_dict["input_tokens"],
            output_tokens=note_dict["output_tokens"],
            cost=note_dict["cost"],
            model=note_dict["model"],
        )
        audio_note.save()

        # Return the ID of the created note
        return str(audio_note.id)  # or audio_note.pk for primary key

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


def delete_note(practice_id: str, file_id: str):
    note_to_delete = AudioNote.objects(id=file_id, practice_id=practice_id).first()

    if not note_to_delete:
        raise HTTPException(status_code=404, detail="No note with that id found in practice")

    # Delete the note document
    note_to_delete.delete()


def retrieve_all_users_notes(user_id: str = None, practice_id: str = None):
    try:
        if not user_id:
            # Gets all practices notes
            notes = AudioNote.objects(practice_id=practice_id).only("patient_id", "transcript", "createdAt").order_by("-createdAt").select_related()
        else:
            # Gets all users notes
            notes = AudioNote.objects(user_id=user_id).only("patient_id", "transcript", "createdAt").order_by("-createdAt").select_related()

    except DoesNotExist as e:
        # Check if the exception is related to User or Letter
        if "User" in str(e):
            raise HTTPException(status_code=404, detail="User not found") from None
        elif "Letter" in str(e):
            raise HTTPException(status_code=404, detail="No letter found") from None
        else:
            raise e

    # Transform the MongoEngine documents to a list of dictionaries
    notes_list = []
    for note in notes:
        created_at = note.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        note_dict = note.to_mongo().to_dict()
        note_dict["createdAt"] = created_at
        note_dict["_id"] = str(note_dict["_id"])
        patient_details = note.patient_id.to_mongo().to_dict()
        del patient_details["_id"]
        if "practice_id" in patient_details:
            del patient_details["practice_id"]
        del patient_details["dob"]
        del patient_details["gender"]
        del patient_details["address"]
        del patient_details["email"]
        note_dict["patient_details"] = patient_details
        del note_dict["patient_id"]
        if not isinstance(note.formatted_notes, str):
            for i in range(len(note.formatted_notes)):
                note_dict["formatted_notes"][i]["note_prompt_id"] = str(note_dict["formatted_notes"][i]["note_prompt_id"])

        notes_list.append(note_dict)

    return notes_list


# Function to get a specific note
def retrieve_note(note_id: str, practice_id: str):
    # Query the note using MongoEngine
    note = (
        AudioNote.objects(id=note_id, practice_id=practice_id)
        .only("patient_id", "formatted_notes", "transcript", "createdAt", "input_tokens", "output_tokens", "cost", "model")
        .first()
        .select_related(2)
    )

    if not note:
        # Handle case where the note doesn't exist or doesn't belong to the user
        raise HTTPException(status_code=400, detail="No note found")

    created_at = note.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
    note_dict = note.to_mongo().to_dict()
    note_dict["createdAt"] = created_at
    note_dict["_id"] = str(note_dict["_id"])
    patient_details = note.patient_id.to_mongo().to_dict()
    del patient_details["_id"]
    if "practice_id" in patient_details:
        del patient_details["practice_id"]
    del patient_details["dob"]
    del patient_details["gender"]
    del patient_details["address"]
    note_dict["patient_details"] = patient_details
    del note_dict["patient_id"]
    if not isinstance(note.formatted_notes, str):
        for i in range(len(note.formatted_notes)):
            note_dict["formatted_notes"][i]["note_prompt_id"] = str(note_dict["formatted_notes"][i]["note_prompt_id"])
            note_dict["formatted_notes"][i]["title"] = note.formatted_notes[i].note_prompt_id.title

    return note_dict


# Function to get a specific note's audio
def retrieve_note_audio(note_id: str, practice_id: str):
    # Query the note using MongoEngine
    note = AudioNote.objects(id=note_id, practice_id=practice_id).only("audio").first()

    if not note:
        # Handle case where the note doesn't exist or doesn't belong to the user
        raise HTTPException(status_code=400, detail="No note found")

    return note.audio


def retrieve_last_three_notes(user_id: str):
    try:
        notes = (
            AudioNote.objects(user_id=user_id)
            .only("patient_id", "formatted_notes", "transcript", "createdAt", "input_tokens", "output_tokens", "cost", "model")
            .order_by("-_id")
            .limit(3)
            .select_related(2)
        )

        notes_list = []

    except DoesNotExist:
        # Handle the case where no notes are found
        return []

    for note in notes:
        created_at = note.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        note_dict = note.to_mongo().to_dict()
        note_dict["createdAt"] = created_at
        note_dict["_id"] = str(note.id)
        patient_details = note.patient_id.to_mongo().to_dict()
        del patient_details["_id"]
        if "practice_id" in patient_details:
            del patient_details["practice_id"]
        note_dict["patient_details"] = patient_details
        del note_dict["patient_id"]
        if not isinstance(note.formatted_notes, str):
            for i in range(len(note.formatted_notes)):
                note_dict["formatted_notes"][i]["note_prompt_id"] = str(note_dict["formatted_notes"][i]["note_prompt_id"])

        notes_list.append(note_dict)

    return notes_list


def retrieve_notes_alphabet_status(user_id: str = None, practice_id: str = None):
    try:
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
            {"$unwind": "$patient"},
            {"$group": {"_id": {"$substr": ["$patient.forename", 0, 1]}, "count": {"$sum": 1}}},
        ]

        if practice_id:
            pipeline = [
                {"$match": {"practice_id": ObjectId(practice_id)}},
                {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
                {"$unwind": "$patient"},
                {"$group": {"_id": {"$substr": ["$patient.forename", 0, 1]}, "count": {"$sum": 1}}},
            ]

        result = AudioNote.objects.aggregate(*pipeline)

        # Create a dictionary with default value 0 for all letters
        alphabet_status = {letter: 0 for letter in ascii_lowercase}

        # Update the dictionary based on the aggregation result
        for entry in result:
            first_letter = entry["_id"].lower()
            count = entry["count"]
            alphabet_status[first_letter] = count if count > 0 else 0

        return alphabet_status

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Error retrieving alphabet_status") from None


def retrieve_all_users_notes_filtered_by_char(starts_with: str, user_id: str = None, practice_id: str = None):
    try:
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
            {"$unwind": "$patient"},
            {"$match": {"patient.forename": {"$regex": f"^{starts_with}", "$options": "i"}}},
            {"$sort": {"createdAt": -1}},
            {"$project": {"audio": 0, "practice_id": 0, "user_id": 0, "formatted_notes": 0}},
        ]
        if practice_id:
            pipeline = [
                {"$match": {"practice_id": ObjectId(practice_id)}},
                {"$lookup": {"from": "patients", "localField": "patient_id", "foreignField": "_id", "as": "patient"}},
                {"$unwind": "$patient"},
                {"$match": {"patient.forename": {"$regex": f"^{starts_with}", "$options": "i"}}},
                {"$sort": {"createdAt": -1}},
                {"$project": {"audio": 0, "practice_id": 0, "user_id": 0, "formatted_notes": 0}},
            ]

        notes = AudioNote.objects.aggregate(*pipeline)

        result = []
        for note in notes:
            result.append(
                {
                    "_id": str(note["_id"]),
                    "transcript": note["transcript"],
                    "patient_details": {
                        "forename": note["patient"]["forename"],
                        "surname": note["patient"]["surname"],
                    },
                    "createdAt": note["createdAt"],
                }
            )

        return result

    except DoesNotExist as e:
        if "Letter" in str(e):
            raise HTTPException(status_code=404, detail="No letter found") from None
        else:
            raise e


def retrieve_patients_last_three_notes(patient_id: str):
    try:
        notes = (
            AudioNote.objects(patient_id=patient_id)
            .only("patient_id", "formatted_notes", "transcript", "createdAt")
            .order_by("-_id")
            .limit(3)
            .select_related()
        )

    except DoesNotExist:
        # Handle the case where no letters are found
        return []

    notes_list = []
    for note in notes:
        created_at = note.id.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        note_dict = note.to_mongo().to_dict()
        note_dict["createdAt"] = created_at
        note_dict["_id"] = str(note_dict["_id"])
        patient_details = note.patient_id.to_mongo().to_dict()
        del patient_details["_id"]
        if "practice_id" in patient_details:
            del patient_details["practice_id"]
        del patient_details["dob"]
        del patient_details["gender"]
        del patient_details["address"]
        del patient_details["email"]
        note_dict["patient_details"] = patient_details
        del note_dict["patient_id"]
        if not isinstance(note.formatted_notes, str):
            for i in range(len(note.formatted_notes)):
                note_dict["formatted_notes"][i]["note_prompt_id"] = str(note_dict["formatted_notes"][i]["note_prompt_id"])

        notes_list.append(note_dict)

    return notes_list


def retrieve_audio_note_time_for_billing_cycle(practice_id: str, start_date: datetime, end_date: datetime):
    audio_notes = AudioNote.objects.filter(practice_id=practice_id, createdAt__gte=start_date, createdAt__lte=end_date)

    total_time = sum(note.length_of_recording for note in audio_notes)

    return total_time


# Function to update the consent letter
def update_note(note_id: str, noteObj: Dict[str, Any], practice_id: str):
    # Use MongoEngine to find and update the document
    note = AudioNote.objects(id=note_id, practice_id=practice_id).first()

    if not note:
        raise HTTPException(status_code=404, detail="No note found")

    formatted_notes = []
    for formatted_note in noteObj["formatted_notes"]:
        notePromptOutput = NotePromptOutputs(note_prompt_id=formatted_note["note_prompt_id"], note_text=formatted_note["note_text"])
        formatted_notes.append(notePromptOutput)

    # Update the consent_letter field
    note.transcript = noteObj["transcript"]
    note.formatted_notes = formatted_notes
    note.input_tokens = noteObj["input_tokens"]
    note.output_tokens = noteObj["output_tokens"]
    note.cost = noteObj["cost"]
    note.model = noteObj["model"]
    note.save()


def update_formatted_notes(note_id: str, new_formatted_notes: str):
    try:
        # Fetch the complete document
        audio_note = AudioNote.objects.get(id=note_id)

        if not audio_note:
            raise HTTPException(status_code=404, detail="No audio note found")

        audio_note.formatted_notes = new_formatted_notes

        # Save the updated document
        audio_note.save()

    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error") from None
