from datetime import datetime

from mongoengine import (
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
)

from app.database.schemas.patient import Patient
from app.database.schemas.user import User


class Letter(Document):
    consent_letter = StringField()
    patient_id = ReferenceField(Patient, required=True)
    user_id = ReferenceField(User, required=True)
    createdAt = DateTimeField(default=datetime.utcnow)
    tokens_consumed = IntField(default=0)

    meta = {"collection": "letters"}  # Specify the collection name
