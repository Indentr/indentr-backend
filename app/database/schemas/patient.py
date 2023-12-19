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
    EmailField
)

from app.database.schemas.practice import Practice


class Patient(Document):
    forename = StringField(required=True)
    surname = StringField(required=True)
    dob = DateField()
    gender = StringField()
    address = StringField()
    email = EmailField(required=True, unique=True)
    practice_id = ReferenceField(Practice, required=True)

    meta = {"collection": "patients"}  # Specify the collection name
