from mongoengine import Document, EmbeddedDocument, fields

from app.database.schemas.practice import Practice


class TriageResponse(EmbeddedDocument):
    diagnosis = fields.StringField()
    general_overview = fields.StringField()
    severity = fields.StringField()
    time_urgency = fields.StringField()
    patient_instructions = fields.StringField()


class Triage(Document):
    first_name = fields.StringField()
    last_name = fields.StringField()
    dob = fields.StringField()
    email = fields.EmailField()
    phone_number = fields.StringField()
    practice_id = fields.ReferenceField(Practice)
    triage_response = fields.EmbeddedDocumentField(TriageResponse)
