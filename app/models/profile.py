from typing import Literal

from pydantic import BaseModel


class PriceListItem(BaseModel):
    service: str
    price: str


class UpdateLetterConfigAdjustment(BaseModel):
    formality_level: float
    detail_level: float


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


class TriageSettings(BaseModel):
    primary_color: str
    show_page_runner: bool
    show_requested_date: bool
    show_date_of_birth: bool
    show_gender: bool
    show_phone_number: bool
    show_address: bool
