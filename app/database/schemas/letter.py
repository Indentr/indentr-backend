from datetime import datetime

from mongoengine import (
    DateTimeField,
    Document,
    FloatField,
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
    input_tokens = IntField(default=0)
    output_tokens = IntField(default=0)
    cost = FloatField(default=0)
    model = StringField()
    tokens_consumed = IntField()

    meta = {"collection": "letters"}  # Specify the collection name
