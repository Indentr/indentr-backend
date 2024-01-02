from mongoengine import (
    Document,
    ReferenceField,
    StringField,
)

from app.database.schemas.patient import Patient


class AudioNote(Document):
    patient_id = ReferenceField(Patient, required=True)
    audio = StringField(required=True)  # Storing audio as Base64 string
    transcript = StringField(required=True)
    formatted_notes = StringField(required=True)
