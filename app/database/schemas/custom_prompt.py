from datetime import datetime

from mongoengine import (
    BinaryField,
    DateTimeField,
    Document,
    EmbeddedDocumentField,
    EmbeddedDocumentListField,
    IntField,
    ReferenceField,
    StringField,
)

from app.database.schemas.practice import Practice
from app.database.schemas.user import User


class CustomPrompt(Document):
    user_id = ReferenceField(User, required=True)
    practice_id = ReferenceField(Practice, required=True)
    title = StringField(required=True)
    text = StringField(required=True)

    meta = {"collection": "custom_prompts"}  # Specifies the collection name


