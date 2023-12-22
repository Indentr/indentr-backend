from mongoengine import BooleanField, Document, IntField, ReferenceField, StringField

from app.database.schemas.patient import Patient
from app.database.schemas.practice import Practice


class Triage(Document):
    practice_id = ReferenceField(Practice, required=True)
    patient_id = ReferenceField(Patient)
    diagnosis = StringField()
    general_overview = StringField()
    severity = IntField()
    opened = BooleanField(default=False)

    meta = {"collection": "triage_responses"}
