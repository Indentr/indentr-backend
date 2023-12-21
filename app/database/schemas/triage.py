from mongoengine import (
    Document, 
    EmbeddedDocument,
    ReferenceField,
    StringField,
    IntField,
    BooleanField
)

from app.database.schemas.practice import Practice
from app.database.schemas.patient import Patient
from app.database.schemas.user import User


class Triage(Document):
    practice_id = ReferenceField(Practice, required=True)
    patient_id = ReferenceField(Patient)
    diagnosis = StringField()
    general_overview = StringField()
    severity = IntField()
    opened = BooleanField(default=False)

    meta = {"collection": "triage_responses"}