from mongoengine import Document, EmbeddedDocument, fields


class Triage(Document):
    first_name = fields.StringField()
    last_name = fields.StringField()
    dob = fields.StringField()
    email = fields.EmailField()
    triage_response = fields.EmbeddedDocumentField(TriageResponse)


class TriageResponse(EmbeddedDocument):
    diagnosis = fields.StringField()
    general_overview = fields.StringField()
    severity = fields.StringField()
    time_urgency = fields.StringField()
    patient_instructions = fields.StringField()
