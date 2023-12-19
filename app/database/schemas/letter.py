from datetime import datetime

from mongoengine import (
    DateField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    ReferenceField,
    IntField,
    StringField,
    fields,
)

from app.database.schemas.user import User
from app.database.schemas.patient import Patient



class Letter(Document):
    consent_letter = StringField()
    patient_id = ReferenceField(Patient, required=True)
    user_id = ReferenceField(User, required=True)
    createdAt = DateTimeField(default=datetime.utcnow)
    tokens_consumed = IntField(default=0)

    meta = {"collection": "letters"}  # Specify the collection name
