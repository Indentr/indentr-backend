from datetime import datetime

from mongoengine import (
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


class TranscriptNotePromptOutputs(EmbeddedDocument):
    note_prompt_id = ReferenceField(CustomPrompt, required=True)
    note_text = StringField(required=True)


class AudioTranscriptNote(Document):
    meta = {"collection": "audio_transcription_note"}  # Specify the collection name

    patient_id = ReferenceField(Patient, required=True)
    user_id = ReferenceField(User, required=True)
    practice_id = ReferenceField(Practice, required=True)
    transcript = StringField(required=True)
    formatted_notes = EmbeddedDocumentListField(TranscriptNotePromptOutputs)
    createdAt = DateTimeField(default=datetime.utcnow)
    patient_details = EmbeddedDocumentField(PatientName)
    input_tokens = IntField(default=0)
    output_tokens = IntField(default=0)
    cost = FloatField(default=0)
    model = StringField()
