from typing import Literal

from pydantic import BaseModel


class PriceListItem(BaseModel):
    service: str
    price: str


class UpdateLetterConfig(BaseModel):
    include_image: bool
    patient_address: bool
    date: bool
    salutation: str
    recipient_naming: Literal["first_lastname", "lastname"]
    pricing: bool
    include_insurance_info: bool
    patient_insurance_info: str
    patient_signature: bool
    dentist_signature: bool
    practice_contact_details: bool
    contact_details_text: str
    sign_off: str
    dentist_naming: Literal["dentist_name", "dentist_practice_name", "practice_name"]
