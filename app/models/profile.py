from pydantic import BaseModel
from typing import Literal


class PriceListItem(BaseModel):
    service: str
    price: str


class UpdateLetterConfig(BaseModel):
    patient_address: bool
    date: bool
    salutation: str
    recipient_naming: Literal["first_lastname", "lastname"]
    pricing: bool
    patient_insurance_info: str
    patient_signature: bool
    dentist_signature: bool
    practice_contact_details: bool
    sign_off: str
    dentist_naming: Literal["dentist_name", "dentist_practice_name", "practice_name"]

