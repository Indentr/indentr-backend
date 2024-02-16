from mongoengine import (
    DateField,
    Document,
    EmailField,
    EmbeddedDocument,
    ReferenceField,
    StringField,
)

from app.database.schemas.practice import Practice


class PatientName(EmbeddedDocument):
    forename = StringField(required=True)
    surname = StringField(required=True)


class Patient(Document):
    forename = StringField(required=True)
    surname = StringField(required=True)
    dob = DateField()
    gender = StringField()
    address = StringField()
    email = EmailField(required=True, unique=True)
    practice_id = ReferenceField(Practice)

    meta = {"collection": "patients"}  # Specify the collection name
