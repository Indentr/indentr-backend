from mongoengine import Document, StringField


class AudioNote(Document):
    patient_id = StringField(required=True)
    audio = StringField(required=True)  # Storing audio as Base64 string
    transcript = StringField(required=True)
    formatted_notes = StringField(required=True)
