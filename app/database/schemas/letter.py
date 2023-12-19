from datetime import datetime

from mongoengine import (
    DateField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    IntField,
    StringField,
    fields,
)

from app.database.schemas.user import User


class PatientInfo(EmbeddedDocument):
    forename = StringField()
    surname = StringField()
    dob = DateField()
    gender = StringField()
    address = StringField()


class Letter(Document):
    consent_letter = StringField()
    patient_info = EmbeddedDocumentField(PatientInfo)
    user_id = fields.ReferenceField(User, required=True)
    createdAt = DateTimeField(default=datetime.utcnow)
    tokens_consumed = IntField(default=0)

    meta = {"collection": "letters"}  # Specify the collection name
