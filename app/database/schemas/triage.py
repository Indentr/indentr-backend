from mongoengine import (
    Document, 
    EmbeddedDocument,
    ReferenceField,
    fields
)

from app.database.schemas.practice import Practice
from app.database.schemas.user import User


class Triage(Document):
    practice_id = ReferenceField(Practice, required=True)
    user_id = ReferenceField(User, required=True)
    diagnosis = fields.StringField()
    general_overview = fields.StringField()
    severity = fields.IntField()
    time_urgency = fields.StringField()
    patient_instructions = fields.StringField()

    meta = {"collection": "triage_responses"}  # Specify the collection name