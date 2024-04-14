# Letter config Settings CRUD file
# -- Files must start with either create, retrieve, update, delete

import base64

from fastapi import HTTPException
from mongoengine import DoesNotExist

from app.database.schemas.letter_config import LetterConfig

def create_letter_config(practice_id: str):
    try:
        letter_config = LetterConfig(practice_id=practice_id)
        letter_config.save()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


def retrieve_letter_config(practice_id: str):
    try:
        # Fetch pricing documents for the given practice_id
        letter_config = LetterConfig.objects(practice_id=practice_id).first().select_related()

        if not letter_config:
            # Handle case where the letter doesn't exist or doesn't belong to the user
            raise HTTPException(status_code=400, detail="No letter config found")

        letter_config_dict = letter_config.to_mongo().to_dict()

        # Encode to base64 string before sending back
        if "image" in letter_config_dict:
            image_data = letter_config_dict["image"]
            letter_config_dict["image"] = base64.b64encode(image_data).decode("utf-8")

        del letter_config_dict["_id"]
        del letter_config_dict["practice_id"]

        return letter_config_dict

    except Exception as e:
        # Handle any other exceptions that might occur
        raise HTTPException(status_code=500, detail=str(e)) from None


def update_letter_image(practice_id: str, image_data: bytes):
    letter_config = LetterConfig.objects(practice_id=practice_id).first()

    if not letter_config:
        raise HTTPException(status_code=404, detail="LetterConfig not found for practice_id")

    letter_config.image = image_data
    letter_config.save()


def update_letter_config_adjustments(practice_id: str, formality_level: float, detail_level: float):
    try:
        letter_config = LetterConfig.objects.get(practice_id=practice_id)
        letter_config.formality_level = formality_level
        letter_config.detail_level = detail_level
        letter_config.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Letter config not found") from None


def update_letter_config(
    practice_id: str,
    include_image: bool,
    patient_address: bool,
    date: bool,
    salutation: str,
    recipient_naming: str,
    pricing: bool,
    include_insurance_info: bool,
    patient_insurance_info: str,
    patient_signature: bool,
    dentist_signature: bool,
    practice_contact_details: bool,
    contact_details_text: str,
    sign_off: str,
    dentist_naming: str,
):
    try:
        letter_config = LetterConfig.objects.get(practice_id=practice_id)
        letter_config.include_image = include_image
        letter_config.patient_address = patient_address
        letter_config.date = date
        letter_config.salutation = salutation
        letter_config.recipient_naming = recipient_naming
        letter_config.pricing = pricing
        letter_config.include_insurance_info = include_insurance_info
        letter_config.patient_insurance_info = patient_insurance_info
        letter_config.patient_signature = patient_signature
        letter_config.dentist_signature = dentist_signature
        letter_config.practice_contact_details = practice_contact_details
        letter_config.contact_details_text = contact_details_text
        letter_config.sign_off = sign_off
        letter_config.dentist_naming = dentist_naming
        letter_config.save()

    except DoesNotExist:
        raise HTTPException(status_code=404, detail="Letter config not found") from None
