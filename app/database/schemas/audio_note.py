from datetime import datetime

from mongoengine import (
    BinaryField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    EmbeddedDocumentListField,
    IntField,
    ReferenceField,
    StringField,
    signals,
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

    @classmethod
    def remove_references_from_audio_notes(cls, sender, document, **kwargs):
        try:
            custom_prompt_id = document.id
            audio_notes = AudioNote.objects(formatted_notes__note_prompt_id=custom_prompt_id)

            for audio_note in audio_notes:
                updated_notes = []

                # Iterate through formatted_notes and only keep the ones that do not match the custom_prompt_id
                for note in audio_note.formatted_notes:
                    if str(note.note_prompt_id.id) != str(custom_prompt_id):
                        updated_notes.append(note)

                audio_note.formatted_notes = updated_notes
                audio_note.save()

        except Exception as e:
            print(e)


# Connect the signal handler to the pre_delete signal for the CustomPrompt model
signals.pre_delete.connect(AudioNote.remove_references_from_audio_notes, sender=CustomPrompt)
