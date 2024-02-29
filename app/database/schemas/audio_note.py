from datetime import datetime

from mongoengine import (
    BinaryField,
    DateTimeField,
    Document,
    EmbeddedDocumentField,
    ReferenceField,
    StringField,
)

from app.database.schemas.patient import Patient, PatientName
from app.database.schemas.practice import Practice
from app.database.schemas.user import User


class AudioNote(Document):
    patient_id = ReferenceField(Patient, required=True)
    user_id = ReferenceField(User, required=True)
    practice_id = ReferenceField(Practice, required=True)
    audio = BinaryField(required=True)
    transcript = StringField(required=True)
    formatted_notes = StringField(required=True)
    createdAt = DateTimeField(default=datetime.utcnow)
    patient_details = EmbeddedDocumentField(PatientName)

    meta = {"collection": "audio_note"}  # Specify the collection name
