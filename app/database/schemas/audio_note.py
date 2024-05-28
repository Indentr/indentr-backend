from datetime import datetime

from mongoengine import (
    BinaryField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    EmbeddedDocumentListField,
    FloatField,
    IntField,
    ReferenceField,
    StringField,
)

from app.database.schemas.custom_prompt import CustomPrompt
from app.database.schemas.patient import Patient, PatientName
from app.database.schemas.practice import Practice
from app.database.schemas.user import User


class NotePromptOutputs(EmbeddedDocument):
    note_prompt_id = ReferenceField(CustomPrompt, required=True)
    note_text = StringField(required=True)


class AudioNote(Document):
    meta = {"collection": "audio_note"}  # Specify the collection name

    patient_id = ReferenceField(Patient, required=True)
    user_id = ReferenceField(User, required=True)
    practice_id = ReferenceField(Practice, required=True)
    audio = BinaryField(required=True)
    transcript = StringField(required=True)
    formatted_notes = EmbeddedDocumentListField(NotePromptOutputs)
    createdAt = DateTimeField(default=datetime.utcnow)
    patient_details = EmbeddedDocumentField(PatientName)
    length_of_recording = IntField()
    input_tokens = IntField(default=0)
    output_tokens = IntField(default=0)
    cost = FloatField(default=0)
    model = StringField()
