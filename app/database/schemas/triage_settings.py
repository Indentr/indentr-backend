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

    # New fields
    show_date_of_birth = BooleanField(default=False)  # Default to False if not provided
    show_gender = BooleanField(default=False)  # Default to False
    show_phone_number = BooleanField(default=False)  # Default to False
    show_address = BooleanField(default=False)  # Default to False

    meta = {"collection": "triage_settings"}
