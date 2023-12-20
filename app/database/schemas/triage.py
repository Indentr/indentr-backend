from mongoengine import (
    Document, 
    EmbeddedDocument,
    ReferenceField,
    fields
)

from app.database.schemas.practice import Practice
from app.database.schemas.patient import Patient
from app.database.schemas.user import User


class Triage(Document):
    practice_id = ReferenceField(Practice, required=True)
    patient_id = ReferenceField(Patient)
    diagnosis = fields.StringField()
    general_overview = fields.StringField()
    severity = fields.IntField()

    meta = {"collection": "triage_responses"}