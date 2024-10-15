from datetime import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    EmbeddedDocumentField,
    IntField,
    ReferenceField,
    StringField,
)

from app.database.schemas.patient import Patient, PatientName
from app.database.schemas.practice import Practice


class Triage(Document):
    practice_id = ReferenceField(Practice, required=True)
    patient_id = ReferenceField(Patient, required=True)
    phone = StringField()
    reason_for_request = StringField()
    diagnosis = StringField()
    general_overview = StringField()
    severity = IntField()
    opened = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    requested_date = DateTimeField()
    GPT_QA = StringField()
    folder = StringField(default="ongoing")
    patient_details = EmbeddedDocumentField(PatientName)
    instruction = BooleanField(default=False)
    patient_instruction = StringField()

    meta = {"collection": "triage_responses"}
