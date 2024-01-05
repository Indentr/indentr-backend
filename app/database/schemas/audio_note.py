from datetime import datetime
from mongoengine import (
    DateTimeField,
    Document,
    ReferenceField,
    StringField,
    BinaryField
)

from app.database.schemas.patient import Patient
from app.database.schemas.user import User
from app.database.schemas.practice import Practice


class AudioNote(Document):
    patient_id = ReferenceField(Patient, required=True)
    user_id = ReferenceField(User, required=True)
    practice_id = ReferenceField(Practice, required=True)
    audio = BinaryField(required=True)  # Storing audio as Base64 string
    transcript = StringField(required=True)
    formatted_notes = StringField(required=True)
    createdAt = DateTimeField(default=datetime.utcnow)
