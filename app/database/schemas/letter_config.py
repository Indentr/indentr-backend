from datetime import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
)

from app.database.schemas.practice import Practice


class LetterConfig(Document):
    RECIPIENT_NAMING = ("first_lastname", "lastname")
    DENTIST_NAMING = ("dentist_name", "dentist_practice_name", "practice_name")

    practice_id = ReferenceField(Practice, required=True)
    patient_address = BooleanField(default=True)
    date = BooleanField(default=False)
    salutation = StringField(default='Dear')
    recipient_naming = StringField(choices=RECIPIENT_NAMING, required=True, default='first_lastname')
    pricing = BooleanField(default=False)
    patient_insurance_info = StringField(default='')
    patient_signature = BooleanField(default=True)
    dentist_signature = BooleanField(default=True)
    practice_contact_details = BooleanField(default=True)
    sign_off = StringField(default='From')
    dentist_naming = StringField(choices=DENTIST_NAMING, required=True, default='dentist_name')


    meta = {"collection": "letter_config"}  # Specify the collection name
