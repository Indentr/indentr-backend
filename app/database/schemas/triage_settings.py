from mongoengine import (
    BooleanField,
    Document,
    ReferenceField,
    StringField,
)

from app.database.schemas.practice import Practice


class TriageSettings(Document):
    practice_id = ReferenceField(Practice, required=True)
    primary_color = StringField(default="#1a73e8")
    show_page_runner = BooleanField(default=True)
    show_requested_date = BooleanField(default=True)

    meta = {"collection": "triage_settings"}
